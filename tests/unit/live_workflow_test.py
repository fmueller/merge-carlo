"""Offline contracts for the local authorized-repository workflow runner."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self, cast
from uuid import uuid4

import pytest

from merge_carlo.configuration import load_scenario_config
from merge_carlo.store import Manifest, WorkspaceKey
from scripts import run_live_workflow as workflow

pytestmark = pytest.mark.unit


def _manifest() -> Manifest:
    return Manifest(
        id=uuid4(),
        repository_id=91,
        api_version="2022-11-28",
        analysis_start=datetime(2026, 4, 1, tzinfo=UTC),
        analysis_end=datetime(2026, 9, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 2, tzinfo=UTC),
    )


def _projected_data(status: str = "complete") -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest": {},
        "pull_requests": [],
        "reviews": [{"user": {"id": "a" * 64}}],
        "lifecycle_events": [],
        "ci_observations": [],
        "derived_features": [
            {
                "readiness_basis": "observed_event",
                "readiness_policy": "strict",
                "origin": "human",
                "fit_exclusion_reason": None,
            }
        ],
        "collection_status": [
            {
                "kind": "pull_requests",
                "pr_id": None,
                "status": status,
                "reason": "record_limit" if status != "complete" else None,
            },
            {
                "kind": "reviews",
                "pr_id": 1,
                "status": status,
                "reason": "record_limit" if status != "complete" else None,
            },
            {
                "kind": "lifecycle_events",
                "pr_id": 1,
                "status": status,
                "reason": "record_limit" if status != "complete" else None,
            },
            {"kind": "ci_observations", "pr_id": 1, "status": "not_requested", "reason": None},
        ],
    }


class _FakeTransport:
    def __init__(self, **_: Any) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: Any) -> None:
        pass


class _FakeStore:
    data: dict[str, object] = _projected_data()
    manifest = _manifest()

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def export(self, _extraction_id: object) -> dict[str, object]:
        return self.data

    def content_hash(self, _extraction_id: object) -> str:
        return "b" * 64


def _options(tmp_path: Path) -> workflow.RunnerOptions:
    output = tmp_path / "out"
    scenarios = tmp_path / "scenarios.yaml"
    scenarios.write_text("schema_version: 1\nscenarios: []\n", encoding="utf-8")
    namespace = workflow._parser().parse_args(
        ["--repo", "example/repo", "--out", str(output), "--scenarios", str(scenarios)]
    )
    options = workflow._options(namespace)
    output.mkdir()
    return options


def _patch_common(monkeypatch: pytest.MonkeyPatch, data: dict[str, object], tmp_path: Path) -> None:
    _FakeStore.data = data
    _FakeStore.manifest = _manifest()
    monkeypatch.setattr(workflow, "GitHubTransport", _FakeTransport)
    monkeypatch.setattr(workflow, "ProjectedStore", _FakeStore)
    monkeypatch.setattr(workflow, "collect_cohort", lambda *_args, **_kwargs: _FakeStore.manifest)

    def write_inspection(dataset: Path, out: Path) -> None:
        assert dataset.is_relative_to(tmp_path / "out")
        out.mkdir(parents=True)
        (out / "report.md").write_text("# inspection\n", encoding="utf-8")

    def build_features(*_args: Any, **_kwargs: Any) -> object:
        return object()

    def calibrate_model(*_args: Any, **_kwargs: Any) -> object:
        return object()

    def write_calibration(_result: object, out: Path) -> None:
        out.mkdir(parents=True)
        (out / "model.json").write_text("{}", encoding="utf-8")
        (out / "model-card.md").write_text("# model\n", encoding="utf-8")

    def simulate(_model: Path, _scenarios: Path, out: Path) -> None:
        out.mkdir(parents=True)
        (out / "report.md").write_text("# experiment\n", encoding="utf-8")

    monkeypatch.setattr(workflow, "write_inspection", write_inspection)
    monkeypatch.setattr(workflow, "build_features", build_features)
    monkeypatch.setattr(workflow, "calibrate_model", calibrate_model)
    monkeypatch.setattr(workflow, "write_calibration", write_calibration)
    monkeypatch.setattr(workflow, "simulate", simulate)


def test_complete_collection_reaches_simulation_and_writes_safe_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = "local-secret-token"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    options = _options(tmp_path)
    _patch_common(monkeypatch, _projected_data(), tmp_path)
    key = WorkspaceKey.create(tmp_path / "private")

    result = workflow._run_repository("example/repo", options, key)

    assert result.status == "simulated"
    assert result.report is not None and result.report.is_file()
    assert result.model is not None and result.model.is_file()
    assert result.human_reviewers is not None and result.human_reviewers.read_text(encoding="utf-8") == "[]\n"
    artifacts = cast(dict[str, object], result.as_dict(options.output)["artifacts"])
    assert artifacts["report"] == "example__repo/experiment/report.md"
    assert artifacts["human_reviewers"] == "example__repo/inputs/human-reviewers.json"
    assert all(token.encode() not in path.read_bytes() for path in options.output.rglob("*") if path.is_file())


def test_partial_collection_blocks_calibration_without_fabricating_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    options = _options(tmp_path)
    _patch_common(monkeypatch, _projected_data("partial"), tmp_path)
    called = False

    def fail_if_called(*_args: Any, **_kwargs: Any) -> object:
        nonlocal called
        called = True
        raise AssertionError("build_features must not run for partial source collections")

    monkeypatch.setattr(workflow, "build_features", fail_if_called)
    key = WorkspaceKey.create(tmp_path / "private")

    result = workflow._run_repository("example/repo", options, key)

    assert result.status == "blocked"
    assert result.stage == "collection"
    assert not called
    assert result.coverage is not None and result.coverage.is_file()
    assert result.model is None
    assert "not run" in (result.error or "")


def test_runner_requires_a_token_and_redacts_it_from_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert workflow.main(["--repo", "example/repo", "--out", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()

    token = "sensitive-token"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    assert token not in workflow._safe_error(ValueError(f"transport failed with {token}"))


def test_runner_rejects_more_than_five_repositories() -> None:
    arguments = [
        item for repository in (f"example/repo-{index}" for index in range(6)) for item in ("--repo", repository)
    ]
    namespace = workflow._parser().parse_args(arguments)

    with pytest.raises(workflow.RunnerInputError, match="between one and five"):
        workflow._options(namespace)


def test_main_continues_after_a_blocked_repository_and_matches_generated_horizon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "local-secret-token")
    calls: list[str] = []

    def run_repository(
        repository: str, _options: workflow.RunnerOptions, _key: WorkspaceKey
    ) -> workflow.RepositoryResult:
        calls.append(repository)
        blocked = repository == "example/blocked"
        return workflow.RepositoryResult(
            repository,
            workflow._repo_slug(repository),
            "blocked" if blocked else "simulated",
            "collection" if blocked else "complete",
            "source collection incomplete" if blocked else None,
        )

    output = tmp_path / "out"
    monkeypatch.setattr(workflow, "_run_repository", run_repository)

    exit_code = workflow.main(
        [
            "--repo",
            "example/blocked",
            "--repo",
            "example/complete",
            "--horizon-days",
            "14",
            "--out",
            str(output),
            "--workspace",
            str(tmp_path / "private"),
        ]
    )

    assert exit_code == 3
    assert calls == ["example/blocked", "example/complete"]
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    repositories = cast(list[dict[str, object]], summary["repositories"])
    assert [item["status"] for item in repositories] == ["blocked", "simulated"]
    scenario = load_scenario_config(output / "default-scenarios.yaml")
    assert scenario.execution is not None
    assert scenario.execution.horizon_days == 14
    assert scenario.execution.warmup_days == 14


def test_runner_rejects_symlinked_repository_output_and_workspace_inside_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out"
    outside = tmp_path / "outside"
    options = _options(tmp_path)
    (output / "example__repo").symlink_to(outside, target_is_directory=True)
    key = WorkspaceKey.create(tmp_path / "private")

    result = workflow._run_repository("example/repo", options, key)

    assert result.status == "blocked"
    assert result.stage == "input"
    assert not outside.exists()

    monkeypatch.setenv("GITHUB_TOKEN", "local-secret-token")
    assert (
        workflow.main(
            [
                "--repo",
                "example/repo",
                "--out",
                str(tmp_path / "new-out"),
                "--workspace",
                str(tmp_path / "new-out" / "private"),
            ]
        )
        == 2
    )
