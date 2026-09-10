"""Command-line entry point; real-data pipeline commands land with their milestones."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from merge_carlo import __version__
from merge_carlo.artifacts import Evidence, write_experiment
from merge_carlo.cohort import SourceError, collect_cohort
from merge_carlo.demo import demo_experiment
from merge_carlo.github import GitHubTransport, TransportLimits
from merge_carlo.store import ProjectedStore, WorkspaceKey

app = typer.Typer(
    name="merge-carlo",
    help="Explore how AI pull-request demand interacts with human review capacity.",
    no_args_is_help=True,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Print the version and exit."),
    ] = False,
) -> None:
    """merge-carlo simulates pull-request review workflows offline."""


@app.command()
def demo(
    out: Annotated[Path, typer.Option(help="Directory for synthetic artifacts; must be empty or absent.")],
    seed: Annotated[int, typer.Option(min=0, help="Root random seed.")] = 42,
    replications: Annotated[int, typer.Option(min=1, help="Paired replications per scenario.")] = 200,
) -> None:
    """Run the SYNTHETIC offline demo without credentials or network access."""
    try:
        write_experiment(demo_experiment(seed, replications), Evidence(synthetic=True, training_cutoff=None), out)
    except (ValueError, OSError) as exc:
        typer.echo(f"Cannot write demo: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"SYNTHETIC demo: {out / 'report.md'}")
    typer.echo("Only the base assumption set was run. Full sensitivity has not been run.")


@app.command()
def collect(
    repo: Annotated[str, typer.Option(help="One authorized GitHub owner/repository.")],
    start: Annotated[str, typer.Option(help="Inclusive timezone-aware analysis start (ISO 8601).")],
    end: Annotated[str, typer.Option(help="Exclusive timezone-aware analysis end (ISO 8601).")],
    out: Annotated[Path, typer.Option(help="Dataset directory; empty or absent unless resuming.")],
    workspace: Annotated[Path, typer.Option(help="Private key directory outside the dataset.")],
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
                    manifest = collect_cohort(transport, store, repo, analysis_start, analysis_end, resume=resume)
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
        typer.echo("Cannot collect: source or access failure.", err=True)
        raise typer.Exit(code=3) from None
    except ValueError:
        typer.echo(
            "Cannot collect: invalid input, unavailable repository, or inaccessible dataset/workspace.", err=True
        )
        raise typer.Exit(code=2) from None
    typer.echo("Collection incomplete; resume to reconcile." if incomplete else "Collection complete.")
    if incomplete:
        raise typer.Exit(code=3)
