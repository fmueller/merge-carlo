"""Artifact publication and artifact-only reporting contracts."""

import csv
import hashlib
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from merge_carlo.artifacts import Evidence, spreadsheet, write_experiment
from merge_carlo.reporting import Summary, render_report, wilson
from merge_carlo.simulation.arrivals import ReplacementAI
from merge_carlo.simulation.calendars import materialize_run_bounds
from merge_carlo.simulation.engine import ReviewBypass, RevisionLoops
from merge_carlo.simulation.runner import AssumptionSet, Experiment, Scenario
from tests.unit.simulation.runner_test import experiment

pytestmark = pytest.mark.unit


def evidence() -> Evidence:
    return Evidence(synthetic=True, training_cutoff="2026-09-07T00:00:00Z")


def test_publish_complete_reproducible_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(experiment(), trace_replications=(1,), scenarios=(Scenario("replacement", ReplacementAI(1)),))
    out = tmp_path / "result"
    write_experiment(config, evidence(), out)
    expected = {
        "manifest.json",
        "resolved-scenarios.json",
        "model-card.json",
        "summary.json",
        "summary.csv",
        "paired-deltas.jsonl",
        "replications.jsonl",
        "report.md",
        "traces.jsonl",
    }
    assert {p.name for p in out.iterdir()} == expected
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["synthetic"] is True
    assert manifest["root_seed"] == 42
    assert manifest["timezone"] == "UTC"
    assert manifest["training_cutoff"] == "2026-09-07T00:00:00Z"
    assert manifest["validation_status"] == "not_performed"
    assert manifest["application_version"] == "0.1.0"
    assert manifest["model_version"] == "fifo-v0.1"
    assert "PCG64" in manifest["rng_scheme"]
    assert "numpy" in manifest["dependency_versions"]
    for name, digest in manifest["content_hashes"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    resolved = json.loads((out / "resolved-scenarios.json").read_text())
    assert resolved["demand_kinds"] == {"replacement": "replacement"}
    traces = [json.loads(line) for line in (out / "traces.jsonl").read_text().splitlines()]
    assert len(traces) == 2
    assert {row["replication"] for row in traces} == {1}

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("reporting must not execute simulation or network")

    monkeypatch.setattr("merge_carlo.simulation.runner.run_experiment", forbidden)
    monkeypatch.setattr("merge_carlo.simulation.engine.run_fifo", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    report = render_report(out)
    assert report == (out / "report.md").read_text()
    assert "Comparison incomplete: false. No policy ranking is produced.\n\n" in report
    assert "| fast | replacement | 2 | 2 | 0 |" in report
    assert "Policy ranking disabled" not in report


def test_refuse_nonempty_and_rollback_failed_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "result"
    out.mkdir()
    (out / "precious").write_text("keep")
    with pytest.raises(FileExistsError):
        write_experiment(experiment(), evidence(), out)
    assert (out / "precious").read_text() == "keep"

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("failed simulation")

    monkeypatch.setattr("merge_carlo.artifacts.run_experiment", fail)
    with pytest.raises(RuntimeError, match="failed simulation"):
        write_experiment(experiment(), evidence(), out, overwrite=True)
    assert list(tmp_path.iterdir()) == [out]
    assert (out / "precious").read_text() == "keep"


def test_wilson_finite_sample_not_certainty() -> None:
    assert wilson(0, 0).estimate.value is None
    assert wilson(0, 0).estimate.reason == "no_defined_replications"
    zero = wilson(0, 10)
    assert zero.estimate.value == 0
    assert zero.low == 0
    assert zero.high == pytest.approx(0.2775328)
    mixed = wilson(3, 10)
    assert mixed.estimate.value == 0.3
    assert mixed.low == pytest.approx(0.1077913)
    assert mixed.high == pytest.approx(0.6032219)
    assert wilson(10, 10).high == pytest.approx(1)


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r", "\n"])
def test_spreadsheet_control_text(prefix: str) -> None:
    assert spreadsheet(prefix + "SUM(1,2)") == "'" + prefix + "SUM(1,2)"
    assert spreadsheet("ordinary") == "ordinary"
    assert spreadsheet("") == ""


def test_aggregate_levels_pairs_and_truncation(tmp_path: Path) -> None:
    config = replace(
        experiment(),
        fixed_horizon_seconds=60,
        assumptions=(
            *experiment().assumptions,
            AssumptionSet("truncated", 10, RevisionLoops(max_review_visits=1, first_change_probability=1)),
        ),
    )
    write_experiment(config, evidence(), tmp_path / "out")
    out = tmp_path / "out"
    summary = Summary.model_validate_json((out / "summary.json").read_bytes())
    rows = {(r.assumption, r.scenario, r.metric): r.summary for r in summary.rows}
    assert summary.requested_replications == 2
    assert summary.comparison_incomplete
    assert summary.limitations == ["engine_truncated", "exploratory_only"]
    assert rows["fast", "baseline", "all_work.merges"].median.value == 2
    assert rows["fast", "baseline", "new_ready.merges"].median.value == 1
    assert rows["fast", "baseline", "all_work.merges"].total == 2  # not twice per scenario
    assert rows["fast", "baseline", "all_work.reviewed.total"].median.value == 2
    assert rows["fast", "baseline", "all_work.reviewed.eligible"].median.value == 2
    assert rows["fast", "baseline", "all_work.reviewed.excluded"].median.value == 0
    assert rows["truncated", "baseline", "all_work.merges"].median.reason == "no_defined_replications"
    assert rows["truncated", "baseline", "all_work.merges"].excluded == 2
    assert rows["truncated", "baseline", "all_work.reviewed.eligible"].median.value is None
    comparisons = {(r.assumption, r.scenario): r for r in summary.comparisons}
    assert comparisons["fast", "bypass"].absolute.median.value == -1
    assert comparisons["fast", "bypass"].relative.median.value == -0.5
    assert comparisons["fast", "bypass"].more_merges.successes == 0
    assert comparisons["slow", "bypass"].absolute.median.value == 1
    assert comparisons["slow", "bypass"].more_merges.successes == 2
    assert comparisons["slow", "bypass"].relative.defined == 0
    assert comparisons["truncated", "bypass"].absolute.defined == 0
    pairs = [json.loads(line) for line in (out / "paired-deltas.jsonl").read_text().splitlines()]
    assert len(pairs) == 12
    assert pairs[0]["absolute"] == {"value": -1, "reason": None}
    assert pairs[0]["relative"] == {"value": -0.5, "reason": None}
    assert next(p for p in pairs if p["assumption"] == "slow")["relative"]["reason"] == "zero_baseline"
    assert next(p for p in pairs if p["assumption"] == "truncated")["absolute"]["reason"] == "engine_truncated"
    assert (out / "traces.jsonl").read_bytes() == b""
    counts = {(c.assumption, c.scenario): (c.usable, c.engine_truncated) for c in summary.replication_counts}
    assert counts["fast", "bypass"] == (2, 0)
    assert counts["truncated", "baseline"] == (0, 2)
    assert counts["truncated", "bypass"] == (2, 0)  # bypass skips the looping review
    report = render_report(out)
    assert "Comparison incomplete: true" in report
    assert "| truncated | baseline | 2 | 0 | 2 |" in report
    assert "| fast | baseline | 2 | 2 | 0 |" in report


def test_overwrite_empty_baseline_only_and_escaped_exports(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    name = "=evil|<script>\n# injected"
    config = replace(experiment(1), assumptions=(AssumptionSet(name, 10),), scenarios=())
    write_experiment(config, evidence(), out)
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    write_experiment(config, evidence(), out, overwrite=True)
    assert first == {p.name: p.read_bytes() for p in out.iterdir()}
    assert list(tmp_path.iterdir()) == [out]
    summary = Summary.model_validate_json(first["summary.json"])
    assert {row.scenario for row in summary.rows} == {"baseline"}
    assert all(row.summary.total == 1 for row in summary.rows)
    assert summary.comparisons[0].absolute.median.value == 0
    with (out / "summary.csv").open(newline="") as source:
        records = list(csv.DictReader(source))
    assert records[0]["assumption"] == "'" + name
    assert "<script>" not in render_report(out)
    assert "\n# injected" not in render_report(out)
    assert "&#124;&#60;script&#62;&#10;&#35; injected" in render_report(out)


def test_publication_rename_failure_restores_previous(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "precious").write_text("keep")
    rename = Path.rename

    def fail_stage(path: Path, target: Path) -> Path:
        if path.name.startswith(".out-") and not path.name.endswith("-previous"):
            raise OSError("publication failed")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_stage)
    with pytest.raises(OSError, match="publication failed"):
        write_experiment(experiment(1), evidence(), out, overwrite=True)
    assert (out / "precious").read_text() == "keep"
    assert list(tmp_path.iterdir()) == [out]


def test_reject_file_and_symlink(tmp_path: Path) -> None:
    file = tmp_path / "file"
    file.write_text("keep")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "missing")
    for out in (file, link):
        with pytest.raises(ValueError, match="directory"):
            write_experiment(experiment(), evidence(), out, overwrite=True)
    assert file.read_text() == "keep"
    assert link.is_symlink()


@pytest.mark.parametrize("basis", ["derived", "proxy", "observed", "assumed"])
def test_declared_template_provenance(tmp_path: Path, basis: str) -> None:
    declared = Evidence.model_validate({"synthetic": False, "training_cutoff": None, "template_basis": basis})
    write_experiment(experiment(1), declared, tmp_path / "out")
    card = json.loads((tmp_path / "out" / "model-card.json").read_text())
    assert card["parameter_basis"]["templates"] == basis


def golden_experiment() -> Experiment:
    return replace(
        experiment(),
        assumptions=(AssumptionSet("fast", 10),),
        scenarios=(Scenario("bypass", bypass=ReviewBypass(1, 0)),),
        trace_replications=(1,),
        fixed_horizon_seconds=60,
    )


def test_golden_bundle_contract(tmp_path: Path) -> None:
    out = tmp_path / "out"
    write_experiment(golden_experiment(), evidence(), out)
    expected = json.loads((Path(__file__).parent / "fixtures" / "experiment-bundle.json").read_text())
    for name, content in expected.items():
        assert (out / name).read_text() == content, name
    manifest = json.loads((out / "manifest.json").read_text())
    assert set(manifest["content_hashes"]) == set(expected) | {"report.md"}
    assert set(manifest["dependency_versions"]) == {"numpy", "simpy", "pydantic", "httpx", "pyyaml", "typer"}
    assert all(manifest["dependency_versions"].values())
    assert manifest["python_version"]
    assert manifest["rng_scheme"] == (
        "SHA-256 canonical ASCII JSON string keys / SeedSequence / PCG64; scenario-independent latent keys"
    )
    templates = json.loads(expected["resolved-scenarios.json"])["experiment"]["templates"]
    canonical = json.dumps(templates, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n"
    assert manifest["dataset_content_hash"] == hashlib.sha256(canonical.encode()).hexdigest()


def truncated_scenario_experiment() -> Experiment:
    # Seed 42: only the load scenario's second replication exhausts verification attempts.
    loops = RevisionLoops(
        author_response_seconds=60, verification_failure_probability=0.05, max_verification_attempts=1
    )
    return replace(experiment(), assumptions=(AssumptionSet("fragile", 10, loops),), trace_replications=(1,))


def test_scenario_only_truncation_gates_comparison_and_keeps_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "out"
    write_experiment(truncated_scenario_experiment(), evidence(), out)
    summary = Summary.model_validate_json((out / "summary.json").read_bytes())
    counts = {c.scenario: (c.assumption, c.requested, c.usable, c.engine_truncated) for c in summary.replication_counts}
    assert counts == {
        "baseline": ("fragile", 2, 2, 0),
        "bypass": ("fragile", 2, 2, 0),
        "load": ("fragile", 2, 1, 1),
    }
    assert summary.comparison_incomplete
    rows = {(r.assumption, r.scenario, r.metric): r.summary for r in summary.rows}
    assert rows["fragile", "load", "all_work.merges"].defined == 1
    assert rows["fragile", "bypass", "all_work.merges"].defined == 2
    comparisons = {r.scenario: r for r in summary.comparisons}
    assert comparisons["load"].absolute.defined == 1
    assert comparisons["load"].more_merges.trials == 1
    assert comparisons["bypass"].absolute.defined == 2
    replications = [json.loads(line) for line in (out / "replications.jsonl").read_text().splitlines()]
    truncated = next(r for r in replications if r["scenario"] == "load" and r["replication"] == 1)
    assert truncated["result"] == {"merges": None, "engine_truncated": True, "metrics": None}
    traces = [json.loads(line) for line in (out / "traces.jsonl").read_text().splitlines()]
    diagnostic = next(t for t in traces if t["scenario"] == "load")["diagnostics"][1]
    assert diagnostic["engine_truncated"] is True
    assert diagnostic["metrics"] is None
    assert sum(p["state"] == "merged" for p in diagnostic["pull_requests"]) == 3  # earlier merges stay diagnostic
    assert sum(r["active_seconds"] for r in diagnostic["reviewers"]) > 0
    report = (out / "report.md").read_text()
    assert report == (Path(__file__).parent / "fixtures" / "experiment-truncated-report.md").read_text()

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("reporting must not execute simulation or network")

    monkeypatch.setattr("merge_carlo.simulation.runner.run_experiment", forbidden)
    monkeypatch.setattr("merge_carlo.artifacts.run_experiment", forbidden)
    monkeypatch.setattr("merge_carlo.simulation.engine.run_fifo", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    assert render_report(out) == report


def test_all_truncated_runs_have_undefined_outcomes(tmp_path: Path) -> None:
    loop = AssumptionSet("loop", 10, RevisionLoops(max_review_visits=1, first_change_probability=1))
    write_experiment(replace(experiment(), assumptions=(loop,), scenarios=()), evidence(), tmp_path / "out")
    summary = Summary.model_validate_json((tmp_path / "out" / "summary.json").read_bytes())
    assert [(c.scenario, c.usable, c.engine_truncated) for c in summary.replication_counts] == [("baseline", 0, 2)]
    assert summary.comparison_incomplete
    assert all(row.summary.defined == 0 and row.summary.median.value is None for row in summary.rows)
    assert all(row.event_probability is None or row.event_probability.trials == 0 for row in summary.rows)
    assert summary.comparisons[0].more_merges.estimate.value is None
    report = render_report(tmp_path / "out")
    assert "| loop | baseline | 2 | 0 | 2 |" in report
    assert "Policy ranking disabled: 2 of 2 runs engine-truncated" in report


def test_record_dst_elapsed_bounds(tmp_path: Path) -> None:
    config = replace(
        experiment(1),
        timezone="Europe/Berlin",
        bounds=materialize_run_bounds(datetime(2026, 3, 29), "Europe/Berlin", horizon_days=1, warmup_days=1),
    )
    write_experiment(config, evidence(), tmp_path / "out")
    resolved = json.loads((tmp_path / "out" / "resolved-scenarios.json").read_text())
    assert resolved["elapsed_seconds"] == {"warmup": 86400, "measurement": 82800}
