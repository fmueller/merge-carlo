#!/usr/bin/env python3
"""Run the authorized GitHub collection-to-simulation workflow locally.

The script deliberately keeps calibration inputs data-only. It reads the
GitHub credential through ``GITHUB_TOKEN`` because the transport owns the
authentication boundary, and it never prints or writes that value.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from merge_carlo.attribution import AttributionConfig
from merge_carlo.calibration import (
    CalibrationAssumptions,
    CalibrationCoverage,
    CollectionStatus,
    ReadinessPolicy,
    calibrate_model,
    load_assumptions,
    write_calibration,
)
from merge_carlo.cohort import SourceError, collect_cohort
from merge_carlo.experiment import simulate
from merge_carlo.features import build_features
from merge_carlo.github import GitHubTransport, TransportLimits
from merge_carlo.inspection import write_inspection
from merge_carlo.store import Manifest, ProjectedStore, StoreError, WorkspaceKey

DEFAULT_REPOSITORIES = (
    "markupsafe/markupsafe",
    "helm/helm",
    "fastapi/fastapi",
    "pandas-dev/pandas",
    "github/codeql",
)
DEFAULT_START = datetime(2026, 4, 1, tzinfo=UTC)
DEFAULT_END = datetime(2026, 9, 1, tzinfo=UTC)
DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_HORIZON_DAYS = 7
_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+")
_COLLECTION_FAMILIES = ("pull_requests", "reviews", "lifecycle_events", "ci_observations")
_SOURCE_FAMILIES = ("pull_requests", "reviews", "lifecycle_events")
_READINESS_BASES = ("observed_event", "supported_reconstruction", "created_at_proxy", "unknown")
_ORIGINS = ("human", "ai", "non_ai_automation", "unknown")
_EXCLUSION_REASONS = ("reopened", "repeated_readiness_cycle", "incomplete_lifecycle", "unknown_readiness")
_DEFAULT_ASSUMPTIONS: dict[str, object] = {
    "review_effort": {
        "human": {"kind": "lognormal", "median_seconds": 900, "sigma": 0.4},
        "ai": {"kind": "lognormal", "median_seconds": 900, "sigma": 0.4},
        "non_ai_automation": {"kind": "lognormal", "median_seconds": 900, "sigma": 0.4},
        "unknown": {"kind": "lognormal", "median_seconds": 900, "sigma": 0.4},
    }
}


class RunnerInputError(ValueError):
    """A static local-input diagnostic suitable for console output."""


@dataclass(frozen=True, slots=True)
class RunnerOptions:
    output: Path
    workspace: Path
    start: datetime
    end: datetime
    cutoff: datetime
    timezone: str
    horizon_days: int
    reviewers: frozenset[str]
    assumptions: CalibrationAssumptions
    attribution: AttributionConfig
    scenarios: Path
    limits: TransportLimits
    resume: bool


@dataclass(frozen=True, slots=True)
class RepositoryResult:
    repository: str
    slug: str
    status: str
    stage: str
    error: str | None = None
    dataset: Path | None = None
    inspection: Path | None = None
    coverage: Path | None = None
    model: Path | None = None
    model_card: Path | None = None
    experiment: Path | None = None
    report: Path | None = None
    reviewer_candidates: Path | None = None
    human_reviewers: Path | None = None

    def as_dict(self, root: Path) -> dict[str, object]:
        def relative(path: Path | None) -> str | None:
            if path is None:
                return None
            return path.relative_to(root).as_posix()

        return {
            "repository": self.repository,
            "slug": self.slug,
            "status": self.status,
            "stage": self.stage,
            "error": self.error,
            "artifacts": {
                "dataset": relative(self.dataset),
                "inspection": relative(self.inspection),
                "coverage": relative(self.coverage),
                "model": relative(self.model),
                "model_card": relative(self.model_card),
                "experiment": relative(self.experiment),
                "report": relative(self.report),
                "reviewer_candidates": relative(self.reviewer_candidates),
                "human_reviewers": relative(self.human_reviewers),
            },
        }


def _parse_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise RunnerInputError(f"invalid {label}; use an ISO-8601 timezone-aware datetime") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RunnerInputError(f"invalid {label}; use an ISO-8601 timezone-aware datetime")
    return parsed.astimezone(UTC)


def _repo_slug(repository: str) -> str:
    if _REPOSITORY_PATTERN.fullmatch(repository) is None or repository.split("/")[1] in {".", ".."}:
        raise RunnerInputError(f"invalid repository: {repository}")
    return repository.replace("/", "__")


def _safe_error(error: BaseException) -> str:
    """Keep exception diagnostics useful without allowing credential leakage."""
    text = str(error).strip() or type(error).__name__
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        text = text.replace(token, "[REDACTED]")
    return text[:500]


def _assert_safe_path(path: Path) -> None:
    """Reject symlinks anywhere in a generated path before following them."""
    current = path
    while True:
        if current.is_symlink():
            raise RunnerInputError("output paths must not contain symlinks")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _read_json(path: Path, label: str) -> object:
    try:
        payload = path.read_bytes()
        if len(payload) > 1_000_000:
            raise RunnerInputError(f"{label} exceeds 1 MiB")
        return json.loads(payload)
    except RunnerInputError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise RunnerInputError(f"invalid {label}") from None


def _load_reviewers(path: Path | None, extra: list[str]) -> frozenset[str]:
    values: set[str] = set(extra)
    if any(not value for value in values):
        raise RunnerInputError("human reviewer identifiers must be non-empty")
    if path is not None:
        data = _read_json(path, "human reviewer file")
        if not isinstance(data, list) or any(not isinstance(value, str) or not value for value in data):
            raise RunnerInputError("human reviewer file must be a JSON array of non-empty strings")
        values.update(data)
    return frozenset(values)


def _load_calibration_assumptions(path: Path | None) -> CalibrationAssumptions:
    data = _DEFAULT_ASSUMPTIONS if path is None else _read_json(path, "calibration assumptions")
    try:
        return load_assumptions(data)
    except ValueError as error:
        raise RunnerInputError(_safe_error(error)) from None


def _overall_status(data: dict[str, object], family: str) -> str:
    statuses: list[CollectionStatus] = [
        cast(CollectionStatus, row["status"])
        for row in cast(list[dict[str, object]], data["collection_status"])
        if row.get("kind") == family
    ]
    if not statuses:
        return "not_requested" if family == "ci_observations" else "complete"
    if "partial" in statuses:
        return "partial"
    if "unavailable" in statuses:
        return "unavailable"
    if all(status == "not_requested" for status in statuses):
        return "not_requested"
    if all(status == "complete" for status in statuses):
        return "complete"
    return "partial"


def _coverage(
    repository: str,
    manifest: Manifest,
    data: dict[str, object],
    dataset_hash: str,
    readiness_policy: ReadinessPolicy,
) -> CalibrationCoverage:
    features = cast(list[dict[str, object]], data["derived_features"])
    readiness = Counter(cast(str, row["readiness_basis"]) for row in features)
    origins = Counter(cast(str, row["origin"]) for row in features)
    exclusions = Counter(
        cast(str, row["fit_exclusion_reason"]) for row in features if row.get("fit_exclusion_reason") is not None
    )
    return CalibrationCoverage(
        dataset_content_hash=dataset_hash,
        repository=repository,
        analysis_start=manifest.analysis_start,
        analysis_end=manifest.analysis_end,
        retrieved_at=manifest.retrieved_at,
        collection_status={
            family: cast(CollectionStatus, _overall_status(data, family)) for family in _COLLECTION_FAMILIES
        },
        readiness_policy=readiness_policy,
        readiness_basis_counts={basis: readiness[basis] for basis in _READINESS_BASES},
        origin_counts={origin: origins[origin] for origin in _ORIGINS},
        lifecycle_exclusion_counts={reason: exclusions[reason] for reason in _EXCLUSION_REASONS},
    )


def _write_json(path: Path, value: object) -> None:
    _assert_safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _reviewer_candidates(data: dict[str, object]) -> list[str]:
    candidates: set[str] = set()
    for row in cast(list[dict[str, object]], data["reviews"]):
        user = row.get("user")
        if isinstance(user, dict) and isinstance(user.get("id"), str):
            candidates.add(user["id"])
    return sorted(candidates)


def _default_scenarios(
    path: Path,
    cutoff: datetime,
    timezone: str,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    replications: int = 50,
) -> Path:
    _assert_safe_path(path)
    try:
        local_start = cutoff.astimezone(ZoneInfo(timezone)).replace(tzinfo=None) + timedelta(days=1)
    except (ZoneInfoNotFoundError, ValueError):
        raise RunnerInputError("invalid timezone") from None
    config = {
        "schema_version": 1,
        "execution": {
            "observation_start": local_start.isoformat(timespec="seconds"),
            "horizon_days": horizon_days,
            "warmup_days": horizon_days,
            "root_seed": 42,
            "replications": replications,
            "calendars": [
                {
                    "name": "weekday-duty",
                    "timezone": timezone,
                    "windows": [
                        {"name": f"weekday-{weekday}", "weekday": weekday, "start": "09:00:00", "end": "17:00:00"}
                        for weekday in range(5)
                    ],
                }
            ],
            "reviewers": [{"name": "reviewer", "calendar": "weekday-duty"}],
        },
        "scenarios": [
            {"name": "additive-ai", "demand": {"kind": "additive_ai", "fraction": 0.25}},
            {"name": "replacement-ai", "demand": {"kind": "replacement_ai", "fraction": 0.25}},
        ],
    }
    if path.exists():
        return path
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def _blocked(
    repository: str,
    slug: str,
    stage: str,
    error: BaseException,
    *,
    dataset: Path | None = None,
    inspection: Path | None = None,
    coverage: Path | None = None,
    model: Path | None = None,
    model_card: Path | None = None,
    experiment: Path | None = None,
    report: Path | None = None,
    reviewer_candidates: Path | None = None,
    human_reviewers: Path | None = None,
) -> RepositoryResult:
    return RepositoryResult(
        repository,
        slug,
        "blocked",
        stage,
        _safe_error(error),
        dataset,
        inspection,
        coverage,
        model,
        model_card,
        experiment,
        report,
        reviewer_candidates,
        human_reviewers,
    )


def _run_repository(repository: str, options: RunnerOptions, key: WorkspaceKey) -> RepositoryResult:
    slug = _repo_slug(repository)
    repo_dir = options.output / slug
    dataset_dir = repo_dir / "dataset"
    dataset_path = dataset_dir / "dataset.sqlite"
    try:
        _assert_safe_path(repo_dir)
        _assert_safe_path(dataset_path)
        if repo_dir.exists() and not options.resume:
            raise RunnerInputError(f"output already exists: {repo_dir}")
        repo_dir.mkdir(parents=True, exist_ok=True)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        if dataset_path.exists() and not options.resume:
            raise RunnerInputError("dataset output already exists")
        if options.resume and not dataset_path.is_file():
            raise RunnerInputError("resume requires an existing dataset")
    except (OSError, RunnerInputError) as error:
        return _blocked(repository, slug, "input", error, dataset=dataset_path)

    try:
        with (
            GitHubTransport(limits=options.limits) as transport,
            ProjectedStore(dataset_path, key, existing_only=options.resume) as store,
        ):
            manifest = collect_cohort(
                transport,
                store,
                repository,
                options.start,
                options.end,
                resume=options.resume,
                attribution=options.attribution,
            )
            data = store.export(manifest.id)
            dataset_hash = store.content_hash(manifest.id)
    except (OSError, SourceError, StoreError, ValueError) as error:
        return _blocked(repository, slug, "collection", error, dataset=dataset_path)

    inspection_dir = repo_dir / "inspection"
    try:
        _assert_safe_path(inspection_dir)
        write_inspection(dataset_path, inspection_dir)
    except (OSError, ValueError) as error:
        return _blocked(repository, slug, "inspection", error, dataset=dataset_path)

    inputs_dir = repo_dir / "inputs"
    coverage_path = inputs_dir / "calibration-coverage.json"
    candidates_path = inputs_dir / "reviewer-candidates.json"
    human_reviewers_path = inputs_dir / "human-reviewers.json"
    try:
        _assert_safe_path(inputs_dir)
        coverage = _coverage(repository, manifest, data, dataset_hash, options.attribution.readiness_policy)
        _write_json(coverage_path, coverage.model_dump(mode="json"))
        _write_json(candidates_path, _reviewer_candidates(data))
        _write_json(human_reviewers_path, sorted(options.reviewers))
        _write_json(inputs_dir / "calibration-assumptions.json", options.assumptions.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as error:
        return _blocked(
            repository,
            slug,
            "calibration-inputs",
            error,
            dataset=dataset_path,
            inspection=inspection_dir / "report.md",
            reviewer_candidates=candidates_path,
            human_reviewers=human_reviewers_path,
        )

    if any(coverage.collection_status[family] in {"partial", "unavailable"} for family in _SOURCE_FAMILIES):
        return _blocked(
            repository,
            slug,
            "collection",
            RunnerInputError("source collection incomplete; calibration and simulation were not run"),
            dataset=dataset_path,
            inspection=inspection_dir / "report.md",
            coverage=coverage_path,
            reviewer_candidates=candidates_path,
            human_reviewers=human_reviewers_path,
        )

    try:
        features = build_features(
            data,
            dataset_content_hash=dataset_hash,
            readiness_policy=coverage.readiness_policy,
            cutoff=options.cutoff,
            timezone=options.timezone,
            outcome_horizon=timedelta(days=options.horizon_days),
            declared_human_reviewers=options.reviewers,
        )
        model_dir = repo_dir / "model"
        _assert_safe_path(model_dir)
        result = calibrate_model(features, options.assumptions, coverage)
        write_calibration(result, model_dir)
    except (OSError, ValueError) as error:
        return _blocked(
            repository,
            slug,
            "calibration",
            error,
            dataset=dataset_path,
            inspection=inspection_dir / "report.md",
            coverage=coverage_path,
            reviewer_candidates=candidates_path,
            human_reviewers=human_reviewers_path,
        )

    experiment_dir = repo_dir / "experiment"
    try:
        _assert_safe_path(experiment_dir)
        simulate(model_dir / "model.json", options.scenarios, experiment_dir)
    except (OSError, ValueError) as error:
        return _blocked(
            repository,
            slug,
            "simulation",
            error,
            dataset=dataset_path,
            inspection=inspection_dir / "report.md",
            coverage=coverage_path,
            model=model_dir / "model.json",
            model_card=model_dir / "model-card.md",
            reviewer_candidates=candidates_path,
            human_reviewers=human_reviewers_path,
        )
    return RepositoryResult(
        repository,
        slug,
        "simulated",
        "complete",
        dataset=dataset_path,
        inspection=inspection_dir / "report.md",
        coverage=coverage_path,
        model=model_dir / "model.json",
        model_card=model_dir / "model-card.md",
        experiment=experiment_dir,
        report=experiment_dir / "report.md",
        reviewer_candidates=candidates_path,
        human_reviewers=human_reviewers_path,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run authorized GitHub collection, inspection, calibration, and simulation locally."
    )
    parser.add_argument(
        "--repo", dest="repositories", action="append", help="OWNER/REPOSITORY (repeat up to five times)"
    )
    parser.add_argument("--start", default=DEFAULT_START.isoformat().replace("+00:00", "Z"), help="Inclusive UTC start")
    parser.add_argument("--end", default=DEFAULT_END.isoformat().replace("+00:00", "Z"), help="Exclusive UTC end")
    parser.add_argument("--cutoff", help="UTC training cutoff; defaults to the interval midpoint")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Model and calendar timezone")
    parser.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS, help="Mature-outcome horizon")
    parser.add_argument("--out", type=Path, default=Path("merge-carlo-live"), help="Output directory")
    parser.add_argument("--workspace", type=Path, help="Private actor-pseudonym key directory")
    parser.add_argument("--attribution-config", type=Path, help="Data-only readiness and actor-origin YAML")
    parser.add_argument("--assumptions", type=Path, help="JSON active-effort assumptions")
    parser.add_argument("--human-reviewers", type=Path, help="JSON array of pseudonymous human reviewer IDs")
    parser.add_argument("--human-reviewer", action="append", default=[], help="One pseudonymous human reviewer ID")
    parser.add_argument("--scenarios", type=Path, help="Scenario YAML; otherwise a local default is generated")
    parser.add_argument("--resume", action="store_true", help="Resume existing per-repository datasets")
    parser.add_argument("--max-pages", type=int, default=100, help="Per-collection page budget")
    parser.add_argument("--max-requests", type=int, default=1000, help="Per-collection request budget")
    parser.add_argument("--max-records", type=int, default=100_000, help="Per-collection record budget")
    parser.add_argument("--max-payload-bytes", type=int, default=8_000_000, help="Per-page payload budget")
    return parser


def _options(namespace: argparse.Namespace) -> RunnerOptions:
    repositories = namespace.repositories or list(DEFAULT_REPOSITORIES)
    if not 1 <= len(repositories) <= 5:
        raise RunnerInputError("provide between one and five --repo values")
    slugs = {_repo_slug(repository) for repository in repositories}
    if len(slugs) != len(repositories):
        raise RunnerInputError("repositories must be unique")
    start = _parse_datetime(namespace.start, "start")
    end = _parse_datetime(namespace.end, "end")
    if start >= end:
        raise RunnerInputError("start must precede end")
    cutoff = _parse_datetime(namespace.cutoff, "cutoff") if namespace.cutoff else start + (end - start) / 2
    if not start <= cutoff <= end:
        raise RunnerInputError("cutoff must be inside the analysis interval")
    if namespace.horizon_days < 1:
        raise RunnerInputError("horizon-days must be positive")
    try:
        ZoneInfo(namespace.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise RunnerInputError("invalid timezone") from None
    try:
        limits = TransportLimits(
            max_pages=namespace.max_pages,
            max_requests=namespace.max_requests,
            max_records=namespace.max_records,
            max_payload_bytes=namespace.max_payload_bytes,
        )
    except ValueError:
        raise RunnerInputError("collection limits must be positive integers") from None
    output = namespace.out
    workspace = namespace.workspace or Path.home() / ".local" / "share" / "merge-carlo" / "workspace"
    if namespace.attribution_config:
        attribution = AttributionConfig.from_yaml(namespace.attribution_config)
    else:
        attribution = AttributionConfig()
    scenarios = namespace.scenarios or output / "default-scenarios.yaml"
    assumptions = _load_calibration_assumptions(namespace.assumptions)
    reviewers = _load_reviewers(namespace.human_reviewers, namespace.human_reviewer)
    return RunnerOptions(
        output=output,
        workspace=workspace,
        start=start,
        end=end,
        cutoff=cutoff,
        timezone=namespace.timezone,
        horizon_days=namespace.horizon_days,
        reviewers=reviewers,
        assumptions=assumptions,
        attribution=attribution,
        scenarios=scenarios,
        limits=limits,
        resume=namespace.resume,
    )


def _workspace(path: Path) -> WorkspaceKey:
    try:
        _assert_safe_path(path)
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        return WorkspaceKey(path) if path.exists() else WorkspaceKey.create(path)
    except StoreError:
        raise
    except OSError:
        raise RunnerInputError("cannot create private workspace") from None


def _write_summary(root: Path, options: RunnerOptions, results: list[RepositoryResult]) -> tuple[Path, Path]:
    payload = {
        "schema_version": 1,
        "analysis": {
            "start": options.start.isoformat(),
            "end": options.end.isoformat(),
            "cutoff": options.cutoff.isoformat(),
            "timezone": options.timezone,
            "outcome_horizon_days": options.horizon_days,
            "declared_human_reviewer_count": len(options.reviewers),
            "held_out_validation": "not_supplied",
        },
        "repositories": [result.as_dict(root) for result in results],
    }
    json_path = root / "summary.json"
    markdown_path = root / "summary.md"
    _assert_safe_path(json_path)
    _assert_safe_path(markdown_path)
    _write_json(json_path, payload)
    lines = [
        "# Local repository workflow",
        "",
        f"- Analysis interval: `{options.start.isoformat()}` to `{options.end.isoformat()}`",
        f"- Training cutoff: `{options.cutoff.isoformat()}`; timezone: `{options.timezone}`",
        f"- Declared human reviewers: `{len(options.reviewers)}`",
        "- Held-out validation: not supplied; reports are exploratory simulation artifacts only.",
        "",
    ]
    for result in results:
        lines.extend((f"## `{result.repository}` — {result.status}", "", f"- Stage: `{result.stage}`"))
        if result.error:
            lines.append(f"- Diagnostic: {result.error}")
        artifacts = result.as_dict(root)["artifacts"]
        assert isinstance(artifacts, dict)
        for name, path in artifacts.items():
            if isinstance(path, str):
                lines.append(f"- [{name}]({path})")
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    namespace = _parser().parse_args(argv)
    try:
        options = _options(namespace)
        if not os.environ.get("GITHUB_TOKEN"):
            raise RunnerInputError("GITHUB_TOKEN is not set; export it in the local shell")
        _assert_safe_path(options.output)
        if options.workspace.resolve(strict=False).is_relative_to(options.output.resolve(strict=False)):
            raise RunnerInputError("private workspace must be outside the output directory")
        if options.output.exists() and (
            not options.output.is_dir() or (not options.resume and any(options.output.iterdir()))
        ):
            raise RunnerInputError("output directory must be absent or empty; choose a new --out")
        options.output.mkdir(parents=True, exist_ok=True)
        if options.scenarios == options.output / "default-scenarios.yaml":
            _default_scenarios(options.scenarios, options.cutoff, options.timezone, options.horizon_days)
        elif not options.scenarios.is_file():
            raise RunnerInputError("scenario file does not exist")
        key = _workspace(options.workspace)
    except (RunnerInputError, OSError, SourceError, StoreError, ValueError) as error:
        print(f"ERROR: {_safe_error(error)}", file=sys.stderr)
        return 2

    results: list[RepositoryResult] = []
    repositories = namespace.repositories or list(DEFAULT_REPOSITORIES)
    for repository in repositories:
        try:
            result = _run_repository(repository, options, key)
        except (OSError, RunnerInputError, ValueError) as error:
            result = _blocked(repository, _repo_slug(repository), "input", error)
        results.append(result)
        print(f"{repository}: {result.status} ({result.stage})")

    try:
        json_path, markdown_path = _write_summary(options.output, options, results)
    except (OSError, TypeError, ValueError) as error:
        print(f"ERROR: cannot write summary: {_safe_error(error)}", file=sys.stderr)
        return 2
    print(f"Summary JSON: {json_path}")
    print(f"Summary Markdown: {markdown_path}")
    if any(result.status == "blocked" for result in results):
        return 3 if any(result.stage == "collection" for result in results) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
