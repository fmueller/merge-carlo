import json
import re
import shlex
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import TypeAdapter
from typer.testing import CliRunner

from merge_carlo.calibration import (
    CalibrationCoverage,
)
from merge_carlo.cli import app
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.store import Batch, Manifest, ProjectedStore, WorkspaceKey
from merge_carlo.validation import (
    ElapsedDelayObservation,
    FrozenReplayModel,
    ObservedOutcomes,
    ReplayArrival,
    ReplayDuty,
    ValidationInput,
    ValidationThresholds,
)

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "docs").is_dir():
    ROOT = ROOT.parent


@pytest.mark.unit
def test_release_status_distinguishes_completed_limited_unsupported_and_remaining_work() -> None:
    status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")

    assert "| M1 |" in status and "| Complete |" in status
    assert "## Verification evidence" in status
    assert "## Limited or unverified" in status
    assert "## Unsupported in v0.1.0" in status
    assert "## Remaining v0.1.0 work" in status
    assert "Live GitHub integration has not been run" in status
    assert "mise run check" in status


@pytest.mark.unit
def test_release_docs_cover_console_contract_and_report_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")
    report = (ROOT / "src" / "merge_carlo" / "reporting.py").read_text(encoding="utf-8")

    for code in ("`0`", "`2`", "`3`", "`4`"):
        assert code in readme
    assert "--json" in readme
    assert "Live GitHub integration has not been run" in readme
    assert "active review effort" in limitations
    assert "defect_escape_rate: null" in report
    assert "Historical fit is not causal validation" in report


@pytest.mark.unit
def test_mutation_discovery_limitations_are_explicit() -> None:
    policy = (ROOT / "docs" / "mutation-policy.md").read_text(encoding="utf-8")
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")

    heading = "## Discovery limitations in v0.1.0"
    assert heading in policy
    section = policy.split(heading, 1)[1].split("\n## ", 1)[0]
    for undiscovered in ("check_probability", "check_summaries", "@app.command", "@app.callback", "@property"):
        assert undiscovered in section
    assert "boxed/mutmut#387" in section
    assert "not mutation-covered" in section
    assert "mutation-policy.md" in limitations


@pytest.mark.unit
def test_performance_benchmark_is_recorded_without_a_runtime_promise() -> None:
    performance = (ROOT / "docs" / "performance.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")

    assert "uv run python -m merge_carlo.benchmark" in performance
    for field in ("wall_seconds", "peak_rss_bytes", "engine_events", "output_bytes", "dependency_versions"):
        assert f'"{field}"' in performance
    assert "No universal runtime" in performance
    assert "## Profile" in performance
    assert "The performance benchmark is not yet recorded" not in status
    assert "docs/performance.md" in status or "(performance.md)" in status


@pytest.mark.unit
def test_calibration_docs_use_the_python_api_and_supported_cli_pipeline() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    calibration = (ROOT / "docs" / "calibration.md").read_text(encoding="utf-8")

    assert "merge-carlo calibrate" not in readme
    for symbol in ("calibrate_model", "load_assumptions", "write_calibration"):
        assert symbol in readme
        assert symbol in calibration
    for artifact in ("model.json", "calibration.json", "model-card.md"):
        assert artifact in readme
    for command in (
        "merge-carlo collect",
        "merge-carlo inspect",
        "merge-carlo validate",
        "merge-carlo simulate",
        "merge-carlo report",
    ):
        assert command in readme
    assert "authorized" in readme
    assert "Live GitHub integration has not been run" in readme
    assert "--dataset data/cohort/dataset.sqlite" in readme
    assert "--dataset data/repository.sqlite" not in readme
    assert _documented_python_source(ROOT / "README.md") == _documented_python_source(ROOT / "docs" / "calibration.md")

    documentation = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    invocation = re.compile(r"^\s*(?:uv run )?merge-carlo calibrate\b")
    for path in documentation:
        in_fence = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                in_fence = not in_fence
            elif in_fence:
                assert not invocation.search(line), path


def _documented_python_source(path: Path) -> str:
    matches = re.findall(r"```python\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)
    assert len(matches) == 1
    source = matches[0]
    assert isinstance(source, str)
    return source


def _synthetic_projected_dataset(tmp_path: Path) -> tuple[Path, Path, str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    workspace_path = tmp_path / "workspace"
    key = WorkspaceKey.create(workspace_path)
    manifest = Manifest(
        id=uuid4(),
        repository_id=17,
        api_version="2022-11-28",
        analysis_start=datetime(2026, 8, 3, tzinfo=UTC),
        analysis_end=datetime(2026, 9, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 2, tzinfo=UTC),
    )
    batches = [
        Batch(
            "pull_requests",
            [
                {
                    "id": 1,
                    "number": 1,
                    "state": "closed",
                    "created_at": "2026-08-04T09:00:00Z",
                    "updated_at": "2026-08-10T12:00:00Z",
                    "observed_at": "2026-08-20T00:00:00Z",
                    "merged_at": "2026-08-05T12:00:00Z",
                    "user": {"id": 101, "type": "User"},
                    "head": {"sha": "a" * 40},
                }
            ],
        ),
        Batch(
            "derived_features",
            [
                {
                    "id": 1,
                    "ready_at": "2026-08-04T09:00:00Z",
                    "readiness_basis": "observed_event",
                    "readiness_policy": "strict",
                    "origin": "human",
                    "origin_basis": "assumed",
                    "fit_eligible": True,
                    "fit_exclusion_reason": None,
                    "basis": "derived",
                }
            ],
            pr_id=1,
        ),
        Batch(
            "reviews",
            [
                {
                    "id": 10,
                    "state": "APPROVED",
                    "submitted_at": "2026-08-04T10:00:00Z",
                    "observed_at": "2026-08-20T00:00:00Z",
                    "user": {"id": 202, "type": "User"},
                }
            ],
            pr_id=1,
        ),
        Batch(
            "lifecycle_events",
            [{"id": 20, "event": "ready_for_review", "created_at": "2026-08-04T09:00:00Z"}],
            pr_id=1,
        ),
        Batch("ci_observations", [], pr_id=1, status="not_requested"),
    ]
    dataset_path = tmp_path / "data" / "dataset.sqlite"
    dataset_path.parent.mkdir()
    with ProjectedStore(dataset_path, key) as store:
        store.save(manifest, batches)
        store.export(manifest.id)
        dataset_hash = store.content_hash(manifest.id)
    return dataset_path, workspace_path, dataset_hash, key.actor(202)


def _write_synthetic_calibration(tmp_path: Path, documentation_path: Path) -> tuple[Path, str]:
    dataset_path, workspace_path, dataset_hash, human_reviewer = _synthetic_projected_dataset(tmp_path)
    coverage = CalibrationCoverage(
        dataset_content_hash=dataset_hash,
        repository="example/repository",
        analysis_start=datetime(2026, 8, 3, tzinfo=UTC),
        analysis_end=datetime(2026, 9, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 2, tzinfo=UTC),
        collection_status={
            "pull_requests": "complete",
            "reviews": "complete",
            "lifecycle_events": "complete",
            "ci_observations": "not_requested",
        },
        readiness_policy="strict",
        readiness_basis_counts={
            "observed_event": 1,
            "supported_reconstruction": 0,
            "created_at_proxy": 0,
            "unknown": 0,
        },
        origin_counts={"human": 1, "ai": 0, "non_ai_automation": 0, "unknown": 0},
        lifecycle_exclusion_counts={"unknown_readiness": 0},
        synthetic_data=True,
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(coverage.model_dump_json(), encoding="utf-8")
    assumptions_data = {
        "review_effort": {
            "human": {"kind": "constant", "seconds": 60},
            "ai": {"kind": "constant", "seconds": 60},
            "non_ai_automation": {"kind": "constant", "seconds": 60},
            "unknown": {"kind": "constant", "seconds": 60},
        }
    }
    assumptions_path = tmp_path / "assumptions.json"
    assumptions_path.write_text(json.dumps(assumptions_data), encoding="utf-8")
    reviewers_path = tmp_path / "reviewers.json"
    reviewers_path.write_text(json.dumps([human_reviewer]), encoding="utf-8")

    calibration_source = _documented_python_source(documentation_path)
    replacements = {
        '"data/cohort/dataset.sqlite"': json.dumps(str(dataset_path)),
        '"/private/path/merge-carlo-key"': json.dumps(str(workspace_path)),
        '"data/cohort/calibration-coverage.json"': json.dumps(str(coverage_path)),
        '"configs/calibration-assumptions.json"': json.dumps(str(assumptions_path)),
        '"configs/human-reviewers.json"': json.dumps(str(reviewers_path)),
        '"models/repository"': json.dumps(str(tmp_path / "models" / "repository")),
        "datetime(2026, 7, 1, tzinfo=UTC)": "datetime(2026, 9, 1, tzinfo=UTC)",
    }
    for source, replacement in replacements.items():
        calibration_source = calibration_source.replace(source, replacement)
    exec(compile(calibration_source, str(documentation_path), "exec"), {"__name__": "__main__"})
    model_dir = tmp_path / "models" / "repository"
    return model_dir, dataset_hash


def _write_synthetic_validation_input(path: Path, dataset_hash: str) -> None:
    request = ValidationInput(
        dataset_content_hash=dataset_hash,
        fitting_interval_start=datetime(2026, 8, 1, tzinfo=UTC),
        training_cutoff=datetime(2026, 9, 1, tzinfo=UTC),
        validation_interval_start=datetime(2026, 9, 7, tzinfo=UTC),
        validation_interval_end=datetime(2026, 9, 14, tzinfo=UTC),
        observed=ObservedOutcomes(1, 1, 1, 1, (60.0,), (1,), 0),
        model=FrozenReplayModel(
            model_version="fifo-v0.1",
            timezone="Europe/Berlin",
            service_seconds=60,
        ),
        arrivals=(ReplayArrival("pr-1", "author", WorkOrigin.HUMAN, datetime(2026, 9, 8, tzinfo=UTC)),),
        benchmark_observations=(
            ElapsedDelayObservation(
                ready_at=datetime(2026, 8, 10, tzinfo=UTC),
                observed_until=datetime(2026, 8, 20, tzinfo=UTC),
                first_review_elapsed_seconds=60,
                completion_category="merged",
                completion_elapsed_seconds=3600,
            ),
        ),
        reviewer_duty=(
            ReplayDuty(
                "reviewer",
                datetime(2026, 9, 7, tzinfo=UTC),
                datetime(2026, 9, 14, tzinfo=UTC),
            ),
        ),
        root_seed=42,
        replications=1,
        thresholds=ValidationThresholds(min_mature_pull_requests=1, min_replications=1),
    )
    payload = TypeAdapter(ValidationInput).dump_python(request, mode="json")
    payload["schema_version"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")


def _documented_cli_args(command: str, documentation_path: Path = ROOT / "README.md") -> list[str]:
    documentation = documentation_path.read_text(encoding="utf-8")
    for block in re.findall(r"```bash\n(.*?)\n```", documentation, re.DOTALL):
        lines = block.splitlines()
        for index, line in enumerate(lines):
            if line != f"uv run merge-carlo {command}" and not line.startswith(f"uv run merge-carlo {command} "):
                continue
            command_lines: list[str] = []
            for candidate in lines[index:]:
                if command_lines and candidate.startswith("uv run merge-carlo "):
                    break
                command_lines.append(candidate)
            command_text = re.sub(r"\\\s*\n\s*", " ", "\n".join(command_lines))
            tokens = shlex.split(command_text)
            assert tokens[:3] == ["uv", "run", "merge-carlo"]
            return tokens[3:]
    raise AssertionError(f"documented {command} command not found")


def _replace_cli_paths(args: list[str], replacements: dict[str, str]) -> list[str]:
    result = list(args)
    for source, target in replacements.items():
        assert source in result
        result = [target if value == source else value for value in result]
    return result


@pytest.mark.unit
def test_documented_persisted_pipeline_smoke_uses_synthetic_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme_model_dir, dataset_hash = _write_synthetic_calibration(tmp_path / "readme-calibration", ROOT / "README.md")
    docs_model_dir, docs_dataset_hash = _write_synthetic_calibration(
        tmp_path / "docs-calibration", ROOT / "docs" / "calibration.md"
    )
    assert docs_dataset_hash != dataset_hash
    scenarios = tmp_path / "scenarios.yaml"
    scenario_text = (ROOT / "examples" / "scenarios.yaml").read_text(encoding="utf-8")
    scenarios.write_text(
        scenario_text.replace("replications: 200", "replications: 1"),
        encoding="utf-8",
    )
    validation_input = tmp_path / "replay-evidence.json"
    _write_synthetic_validation_input(validation_input, dataset_hash)
    docs_validation_input = tmp_path / "docs-replay-evidence.json"
    _write_synthetic_validation_input(docs_validation_input, docs_dataset_hash)
    runner = CliRunner()

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.count("/") == 3:
            return httpx.Response(200, json={"id": 17})
        return httpx.Response(200, json=[])

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))

    collection = tmp_path / "cohort"
    collected = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("collect"),
            {
                "data/cohort": str(collection),
                "/private/path/merge-carlo-key": str(tmp_path / "collection-workspace"),
            },
        ),
    )
    assert collected.exit_code == 0, collected.output
    assert (collection / "dataset.sqlite").is_file()

    inspection = tmp_path / "inspection"
    inspected = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("inspect"),
            {
                "data/cohort/dataset.sqlite": str(collection / "dataset.sqlite"),
                "out/inspection": str(inspection),
            },
        ),
    )
    assert inspected.exit_code == 0, inspected.output
    assert (inspection / "inspection.json").is_file()
    assert (inspection / "report.md").is_file()

    experiment = tmp_path / "experiment"
    simulated = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("simulate"),
            {
                "models/repository/model.json": str(readme_model_dir / "model.json"),
                "configs/scenarios.yaml": str(scenarios),
                "out/experiment": str(experiment),
            },
        ),
    )
    assert simulated.exit_code == 0, simulated.output

    validated = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("validate"),
            {
                "out/replay-evidence.json": str(validation_input),
                "out/validation": str(tmp_path / "validation"),
            },
        ),
    )
    assert validated.exit_code == 0, validated.output

    reported = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("report"),
            {
                "out/experiment": str(experiment),
                "out/validation/validation.json": str(tmp_path / "validation" / "validation.json"),
                "out/experiment/report.md": str(experiment / "report.md"),
            },
        ),
    )
    assert reported.exit_code == 0, reported.output
    report = (experiment / "report.md").read_text(encoding="utf-8")
    assert report.startswith("# Experiment report — SYNTHETIC")
    assert "Validation:" in report

    docs_validated = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("validate"),
            {
                "out/replay-evidence.json": str(docs_validation_input),
                "out/validation": str(tmp_path / "docs-validation"),
            },
        ),
    )
    assert docs_validated.exit_code == 0, docs_validated.output

    docs_experiment = tmp_path / "docs-experiment"
    docs_simulated = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("simulate", ROOT / "docs" / "calibration.md"),
            {
                "models/repository/model.json": str(docs_model_dir / "model.json"),
                "configs/scenarios.yaml": str(scenarios),
                "out/experiment": str(docs_experiment),
            },
        ),
    )
    assert docs_simulated.exit_code == 0, docs_simulated.output

    docs_reported = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("report", ROOT / "docs" / "calibration.md"),
            {
                "out/experiment": str(docs_experiment),
                "out/validation/validation.json": str(tmp_path / "docs-validation" / "validation.json"),
                "out/experiment/report.md": str(docs_experiment / "report.md"),
            },
        ),
    )
    assert docs_reported.exit_code == 0, docs_reported.output
    assert (docs_experiment / "report.md").read_text(encoding="utf-8").startswith("# Experiment report — SYNTHETIC")

    invalid = runner.invoke(
        app,
        _replace_cli_paths(
            _documented_cli_args("simulate"),
            {
                "models/repository/model.json": str(tmp_path / "missing-model.json"),
                "configs/scenarios.yaml": str(scenarios),
                "out/experiment": str(tmp_path / "invalid"),
            },
        ),
    )
    assert invalid.exit_code == 2
