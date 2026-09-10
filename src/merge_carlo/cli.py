"""Command-line entry point; real-data pipeline commands land with their milestones."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from typer._click.exceptions import ClickException

from merge_carlo import __version__
from merge_carlo.artifacts import Evidence, write_experiment
from merge_carlo.attribution import AttributionConfig
from merge_carlo.cohort import SourceError, collect_cohort
from merge_carlo.configuration import export_schemas
from merge_carlo.demo import demo_experiment
from merge_carlo.github import GitHubTransport, TransportLimits
from merge_carlo.inspection import InspectionError, write_inspection
from merge_carlo.store import ProjectedStore, WorkspaceKey
from merge_carlo.validation import load_validation_evidence, run_validation, write_validation


class JsonTyperGroup(typer.core.TyperGroup):
    """Keep Typer's normal errors unless global JSON output was requested."""

    def main(self, *args: Any, **kwargs: Any) -> Any:
        supplied_args = kwargs.get("args", args[0] if args else None)
        arguments = list(sys.argv[1:] if supplied_args is None else supplied_args)
        if "--json" not in arguments:
            return super().main(*args, **kwargs)
        arguments = ["--json", *(argument for argument in arguments if argument != "--json")]
        if args:
            args = (arguments, *args[1:])
        else:
            kwargs["args"] = arguments
        standalone_mode = bool(kwargs.get("standalone_mode", True))
        kwargs["standalone_mode"] = False
        try:
            result = super().main(*args, **kwargs)
        except ClickException as exc:
            typer.echo(json.dumps({"exit_code": exc.exit_code, "message": exc.format_message(), "status": "error"}))
            if standalone_mode:
                raise SystemExit(exc.exit_code) from None
            return exc.exit_code
        if standalone_mode and isinstance(result, int):
            raise SystemExit(result)
        return result


app = typer.Typer(
    name="merge-carlo",
    cls=JsonTyperGroup,
    help="Explore how AI pull-request demand interacts with human review capacity.",
    no_args_is_help=True,
)


def _emit(ctx: typer.Context, message: str, exit_code: int = 0, *, err: bool | None = None) -> None:
    json_output = bool(ctx.find_root().params.get("json_output"))
    if json_output:
        typer.echo(
            json.dumps({"exit_code": exit_code, "message": message, "status": "ok" if exit_code == 0 else "error"})
        )
    else:
        typer.echo(message, err=exit_code != 0 if err is None else err)


def _print_version(ctx: typer.Context, parameter: object, value: bool) -> None:
    if value:
        _emit(ctx, __version__)
        raise typer.Exit(code=0)


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Print the version and exit."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", is_eager=True, help="Write one JSON object per console message."),
    ] = False,
) -> None:
    """merge-carlo simulates pull-request review workflows offline."""


@app.command()
def schema(
    ctx: typer.Context,
    out: Annotated[Path, typer.Option(help="Empty or absent directory for versioned JSON Schemas.")],
) -> None:
    """Export the assumption and scenario configuration JSON Schemas."""
    try:
        export_schemas(out)
    except (OSError, ValueError):
        _emit(ctx, "Cannot export schemas: invalid or inaccessible output.", 2)
        raise typer.Exit(code=2) from None
    _emit(ctx, f"Configuration schemas: {out}")


@app.command()
def demo(
    ctx: typer.Context,
    out: Annotated[Path, typer.Option(help="Directory for synthetic artifacts; must be empty or absent.")],
    seed: Annotated[int, typer.Option(min=0, help="Root random seed.")] = 42,
    replications: Annotated[int, typer.Option(min=1, help="Paired replications per scenario.")] = 200,
) -> None:
    """Run the SYNTHETIC offline demo without credentials or network access."""
    try:
        write_experiment(demo_experiment(seed, replications), Evidence(synthetic=True, training_cutoff=None), out)
    except (ValueError, OSError) as exc:
        _emit(ctx, f"Cannot write demo: {exc}", 2)
        raise typer.Exit(code=2) from exc
    _emit(ctx, f"SYNTHETIC demo: {out / 'report.md'}")
    _emit(ctx, "Only the base assumption set was run. Full sensitivity has not been run.")


@app.command()
def collect(
    ctx: typer.Context,
    repo: Annotated[str, typer.Option(help="One authorized GitHub owner/repository.")],
    start: Annotated[str, typer.Option(help="Inclusive timezone-aware analysis start (ISO 8601).")],
    end: Annotated[str, typer.Option(help="Exclusive timezone-aware analysis end (ISO 8601).")],
    out: Annotated[Path, typer.Option(help="Dataset directory; empty or absent unless resuming.")],
    workspace: Annotated[Path, typer.Option(help="Private key directory outside the dataset.")],
    attribution_config: Annotated[
        Path | None,
        typer.Option(help="Local YAML with readiness policy and explicit actor-origin declarations."),
    ] = None,
    resume: Annotated[bool, typer.Option(help="Reconcile the existing extraction from page one.")] = False,
    api_version: Annotated[str, typer.Option(help="GitHub REST API version.")] = "2022-11-28",
    max_pages: Annotated[int, typer.Option(min=1, help="Page budget per collection.")] = 100,
    max_requests: Annotated[int, typer.Option(min=1, help="Request budget per collection.")] = 1000,
    max_records: Annotated[int, typer.Option(min=1, help="Record budget per collection.")] = 100_000,
    max_payload_bytes: Annotated[int, typer.Option(min=1, help="Payload byte budget per page.")] = 8_000_000,
) -> None:
    """Collect read-only metadata using GITHUB_TOKEN; never infer work origin."""
    try:
        if workspace.resolve().is_relative_to(out.resolve()):
            raise ValueError
        if resume:
            if not out.is_dir() or not (out / "dataset.sqlite").is_file():
                raise ValueError
            if any(path.name not in {"dataset.sqlite", "dataset.sqlite-journal"} for path in out.iterdir()):
                raise ValueError
        elif out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError
        analysis_start, analysis_end = datetime.fromisoformat(start), datetime.fromisoformat(end)
        if analysis_start.tzinfo is None or analysis_end.tzinfo is None or analysis_start >= analysis_end:
            raise ValueError
        attribution = AttributionConfig.from_yaml(attribution_config) if attribution_config else AttributionConfig()
        key = WorkspaceKey(workspace) if workspace.exists() else WorkspaceKey.create(workspace)
        out.mkdir(parents=True, exist_ok=True)
        discard_empty = False
        try:
            with (
                GitHubTransport(
                    api_version=api_version,
                    limits=TransportLimits(
                        max_pages=max_pages,
                        max_requests=max_requests,
                        max_records=max_records,
                        max_payload_bytes=max_payload_bytes,
                    ),
                ) as transport,
                ProjectedStore(out / "dataset.sqlite", key, existing_only=resume) as store,
            ):
                try:
                    manifest = collect_cohort(
                        transport,
                        store,
                        repo,
                        analysis_start,
                        analysis_end,
                        resume=resume,
                        attribution=attribution,
                    )
                    statuses = store.export(manifest.id)["collection_status"]
                    assert isinstance(statuses, list)
                    incomplete = any(row["status"] in {"partial", "unavailable"} for row in statuses)
                finally:
                    discard_empty = not resume and not store.manifests()
        finally:
            # Only discard our newly initialized database, after closing SQLite.
            # A committed incomplete marker or any resumed extraction survives.
            if discard_empty:
                (out / "dataset.sqlite").unlink()
    except (SourceError, OSError):
        _emit(ctx, "Cannot collect: source or access failure.", 3)
        raise typer.Exit(code=3) from None
    except ValueError:
        _emit(ctx, "Cannot collect: invalid input, unavailable repository, or inaccessible dataset/workspace.", 2)
        raise typer.Exit(code=2) from None
    if incomplete:
        _emit(ctx, "Collection incomplete; resume to reconcile.", 3, err=False)
        raise typer.Exit(code=3)
    _emit(ctx, "Collection complete.")


@app.command()
def inspect(
    ctx: typer.Context,
    dataset: Annotated[Path, typer.Option(help="Projected SQLite dataset from collect.")],
    out: Annotated[Path, typer.Option(help="Empty or absent directory for inspection reports.")],
) -> None:
    """Report dataset coverage and quality without the private workspace key."""
    try:
        write_inspection(dataset, out)
    except (InspectionError, OSError):
        _emit(ctx, "Cannot inspect: invalid or inaccessible dataset/output.", 2)
        raise typer.Exit(code=2) from None
    _emit(ctx, f"Dataset inspection: {out / 'report.md'}")


@app.command()
def validate(
    ctx: typer.Context,
    input: Annotated[Path, typer.Option(help="Versioned held-out replay evidence JSON.")],
    out: Annotated[Path, typer.Option(help="Empty or absent directory for validation artifacts.")],
    strict: Annotated[bool, typer.Option(help="Exit 4 when any declared evidence gate fails.")] = False,
) -> None:
    """Apply historical descriptive gates to an offline held-out replay."""
    try:
        result = run_validation(load_validation_evidence(input))
        write_validation(result, out)
    except (OSError, ValueError):
        _emit(ctx, "Cannot validate: invalid or inaccessible evidence/output.", 2)
        raise typer.Exit(code=2) from None
    exit_code = 4 if result.status == "fail" and strict else 0
    _emit(ctx, f"Validation {result.status}: {out / 'report.md'}", exit_code, err=False)
    if exit_code:
        raise typer.Exit(code=exit_code)
    if result.status == "fail":
        _emit(ctx, "Validation failed with warnings; exploratory report was written.")
