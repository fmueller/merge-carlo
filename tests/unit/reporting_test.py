"""Fixed artifact fixture: rendering is independent of simulation."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from merge_carlo.reporting import (
    Comparison,
    Evidence,
    Probability,
    ReplicationCount,
    Summary,
    SummaryRow,
    markdown,
    render_report,
    wilson,
)
from merge_carlo.simulation.metrics import Metric, MetricSummary

pytestmark = pytest.mark.unit


def fixture() -> Summary:
    stats = MetricSummary(10, 8, 2, Metric(3), Metric(1), Metric(9))
    undefined = MetricSummary(10, 0, 10, *(Metric(None, "no_defined_replications") for _ in range(3)))
    return Summary(
        evidence=Evidence(synthetic=True, training_cutoff=None),
        requested_replications=10,
        comparison_incomplete=True,
        limitations=["engine_truncated", "exploratory_only"],
        replication_counts=[
            ReplicationCount(assumption="low", scenario="baseline", requested=10, usable=10, engine_truncated=0),
            ReplicationCount(assumption="low", scenario="load", requested=10, usable=8, engine_truncated=2),
        ],
        rows=[
            SummaryRow(assumption="low", scenario="load", metric="all_work.merges", summary=stats),
            SummaryRow(
                assumption="low",
                scenario="load",
                metric="all_work.backlog_exceeded",
                summary=MetricSummary(10, 8, 2, Metric(0), Metric(0), Metric(1)),
                event_probability=Probability(successes=3, trials=8, estimate=Metric(0.375), low=0.14, high=0.69),
            ),
        ],
        comparisons=[
            Comparison(
                assumption="low",
                scenario="load",
                absolute=undefined,
                relative=undefined,
                more_merges=Probability(
                    successes=0, trials=0, estimate=Metric(None, "no_defined_replications"), low=None, high=None
                ),
            )
        ],
    )


def test_golden_report(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(fixture().model_dump_json())
    actual = render_report(tmp_path)
    assert actual == (Path(__file__).parent / "fixtures" / "experiment-report.md").read_text()
    assert "3 [1, 9]; 8/10 defined" in actual
    assert "3/8; 0.375 [95% Wilson: 0.14, 0.69]" in actual
    assert "0/0; null [95% Wilson: null, null]" in actual
    assert actual.count("— SYNTHETIC") == 7


def test_non_synthetic_report_and_contract_rejection(tmp_path: Path) -> None:
    summary = fixture().model_copy(update={"evidence": Evidence(synthetic=False, training_cutoff="2026-01-02")})
    path = tmp_path / "summary.json"
    path.write_text(summary.model_dump_json())
    report = render_report(tmp_path)
    assert "SYNTHETIC" not in report
    assert report.count("CONDITIONAL MODEL OUTPUT") == 7
    assert "Training cutoff: 2026&#45;01&#45;02" in report
    path.write_text('{"schema_version":2}')
    with pytest.raises(ValidationError):
        render_report(tmp_path)
    path.write_bytes(b" " * (16 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds 16 MiB"):
        render_report(tmp_path)


@pytest.mark.parametrize("successes,trials", [(-1, 3), (4, 3), (0, -1)])
def test_invalid_binomial_counts(successes: int, trials: int) -> None:
    with pytest.raises(ValueError):
        wilson(successes, trials)


def test_escape_all_markdown_syntax() -> None:
    controls = "\\`*_{}[]<>()#+-.!|&\"'\n\r\t\x00\x1f\x7f"
    assert markdown(controls) == "".join(f"&#{ord(c)};" for c in controls)
    assert markdown("word 012 @é") == "word 012 @é"


def test_reproduction_requires_manual_reconstruction(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(fixture().model_dump_json())
    assert "Reconstruct an Experiment manually" in render_report(tmp_path)


@pytest.mark.parametrize("field,value", [("requested_replications", -5), ("requested_replications", 0)])
def test_reject_invalid_requested_count(tmp_path: Path, field: str, value: int) -> None:
    data = fixture().model_dump(mode="json")
    data[field] = value
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        render_report(tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("successes", 9),
        ("trials", -2),
        ("low", -0.1),
        ("high", 1.1),
        ("low", 0.7),
        ("estimate", {"value": 0.9, "reason": None}),
    ],
)
def test_reject_invalid_saved_probability(field: str, value: object) -> None:
    data = {"successes": 3, "trials": 8, "estimate": {"value": 0.375}, "low": 0.14, "high": 0.69}
    data[field] = value
    with pytest.raises(ValidationError):
        Probability.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("low", 0.0),
        ("high", 1.0),
        ("estimate", {"value": 0.0, "reason": None}),
        ("estimate", {"value": None, "reason": "engine_truncated"}),
    ],
)
def test_reject_defined_zero_trial_probability(field: str, value: object) -> None:
    data = {
        "successes": 0,
        "trials": 0,
        "estimate": {"value": None, "reason": "no_defined_replications"},
        "low": None,
        "high": None,
    }
    Probability.model_validate(data)
    data[field] = value
    with pytest.raises(ValidationError, match="zero trials require undefined probability and bounds"):
        Probability.model_validate(data)


@pytest.mark.parametrize(
    "defined,field,value,message",
    [
        (False, "median", {"value": 3}, "undefined summary requires null values and reasons"),
        (False, "low", {"value": None, "reason": "engine_truncated"}, "undefined summary requires null values"),
        (True, "high", {"value": 9, "reason": "no_defined_replications"}, "invalid summary quantiles"),
    ],
)
def test_reject_inconsistent_summary_null_reasons(
    tmp_path: Path, defined: bool, field: str, value: object, message: str
) -> None:
    data = fixture().model_dump(mode="json")
    Summary.model_validate(data)
    summary = data["rows"][0]["summary"] if defined else data["comparisons"][0]["absolute"]
    summary[field] = value
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError, match=message):
        render_report(tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("defined", -1),
        ("excluded", 9),
        ("total", 11),
        ("median", {"value": None}),
        ("low", {"value": 12}),
        ("high", {"value": float("inf")}),
    ],
)
def test_reject_invalid_saved_summary(tmp_path: Path, field: str, value: object) -> None:
    data = fixture().model_dump(mode="json")
    data["rows"][0]["summary"][field] = value
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        render_report(tmp_path)


def test_report_exposes_truncation_counts_and_disables_ranking(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(fixture().model_dump_json())
    report = render_report(tmp_path)
    assert "| Assumption | Scenario | Requested | Usable | Engine-truncated |" in report
    assert "| low | load | 10 | 8 | 2 |" in report
    assert "Policy ranking disabled: 2 of 20 runs engine-truncated" in report
    assert report.index("| low | load | 10 | 8 | 2 |") < report.index("## Scenario comparison")


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda d: d["replication_counts"][1].update(usable=9), "usable and engine-truncated counts must sum"),
        (lambda d: d["replication_counts"][1].update(requested=12, usable=10), "requested replications"),
        (lambda d: d["replication_counts"][1].update(usable=7, engine_truncated=3), "exceed usable replications"),
        (lambda d: d["replication_counts"].pop(0), "missing replication counts"),
        (lambda d: d["replication_counts"].pop(1), "missing replication counts"),
        (lambda d: d["replication_counts"].append(d["replication_counts"][0]), "duplicate replication counts"),
        (lambda d: d.update(comparison_incomplete=False), "engine truncation requires an incomplete comparison"),
        (lambda d: d["replication_counts"][1].update(usable=-1, engine_truncated=11), "greater than or equal to 0"),
    ],
)
def test_reject_inconsistent_saved_replication_counts(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], object], message: str
) -> None:
    data = fixture().model_dump(mode="json")
    mutate(data)
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError, match=message):
        render_report(tmp_path)


def test_reject_paired_defined_beyond_usable_baseline(tmp_path: Path) -> None:
    data = fixture().model_dump(mode="json")
    defined = MetricSummary(10, 10, 0, Metric(0), Metric(0), Metric(0))
    data["comparisons"][0].update(
        absolute=TypeAdapter(MetricSummary).dump_python(defined),
        more_merges=wilson(0, 10).model_dump(mode="json"),
    )
    data["replication_counts"][1].update(usable=10, engine_truncated=0)
    data["replication_counts"][0].update(usable=9, engine_truncated=1)
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError, match="exceed usable replications"):
        render_report(tmp_path)


@pytest.mark.parametrize("paired", [False, True])
def test_reject_probability_denominator_mismatch(tmp_path: Path, paired: bool) -> None:
    data = fixture().model_dump(mode="json")
    if paired:
        data["comparisons"][0]["more_merges"] = wilson(3, 8).model_dump(mode="json")
    else:
        data["rows"][1]["event_probability"] = wilson(30, 80).model_dump(mode="json")
    (tmp_path / "summary.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError, match="probability trials"):
        render_report(tmp_path)
