"""Provenance-preserving empirical model construction."""

import hashlib
import json
import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal

import pytest

from merge_carlo.calibration import (
    CalibrationCoverage,
    CalibrationThresholds,
    calibrate_model,
    load_assumptions,
    render_model_card,
    write_calibration,
)
from merge_carlo.features import FeatureSet, PullRequestFeatures, ReadyToMerge, RequestedChangePrevalence
from merge_carlo.simulation.arrivals import TemplateArrival, WeekTemplate
from merge_carlo.simulation.domain import WorkOrigin

pytestmark = pytest.mark.unit


def features(
    *,
    pulls: int = 4,
    decisions: int = 3,
    weeks: int = 8,
    policy: Literal["strict", "created_at_proxy"] = "strict",
) -> FeatureSet:
    rows = tuple(
        PullRequestFeatures(
            pr_id=index,
            ready_at=datetime(2026, 1, 5, tzinfo=UTC) + timedelta(days=index),
            author_id=f"author-{index}",
            origin=WorkOrigin.HUMAN,
            first_substantive_review_elapsed=timedelta(hours=index + 1) if index < decisions else None,
            first_observed_decision="changes_requested" if index == 0 else "approved" if index < decisions else None,
            comment_only_reviews=0,
            ready_to_merge_elapsed_completion_conditioned=timedelta(days=index + 1) if index % 2 == 0 else None,
            fixed_horizon_eligible=True,
            reviewed_within_horizon=index < decisions,
            merged_within_horizon=index % 2 == 0,
            size_snapshot=None,
        )
        for index in range(pulls)
    )
    templates = tuple(
        WeekTemplate(
            date(2025, 11, 3) + timedelta(weeks=index),
            (TemplateArrival(timedelta(hours=index + 1), f"author-{index}", WorkOrigin.HUMAN),),
        )
        for index in range(weeks)
    )
    return FeatureSet(
        dataset_content_hash="a" * 64,
        readiness_policy=policy,
        training_cutoff=datetime(2026, 1, 19, tzinfo=UTC),
        timezone="Europe/Berlin",
        outcome_horizon=timedelta(days=7),
        week_templates=templates,
        pull_requests=rows,
        requested_change_prevalence=RequestedChangePrevalence(1, decisions, timedelta(days=7)),
        ready_to_merge=ReadyToMerge(
            tuple(
                row.ready_to_merge_elapsed_completion_conditioned
                for row in rows
                if row.ready_to_merge_elapsed_completion_conditioned
            )
        ),
        ci_observations=(),
        ci_coverage=(0, 0),
    )


def coverage(
    *, total: int = 5, unknown: int = 1, policy: Literal["strict", "created_at_proxy"] = "strict"
) -> CalibrationCoverage:
    return CalibrationCoverage(
        dataset_content_hash="a" * 64,
        repository="example/repository",
        analysis_start=datetime(2025, 11, 1, tzinfo=UTC),
        analysis_end=datetime(2026, 2, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 2, 2, tzinfo=UTC),
        collection_status={
            "pull_requests": "complete",
            "reviews": "complete",
            "lifecycle_events": "complete",
            "ci_observations": "not_requested",
        },
        readiness_policy=policy,
        readiness_basis_counts={
            "observed_event": total - unknown,
            "supported_reconstruction": 0,
            "created_at_proxy": 0,
            "unknown": unknown,
        },
        origin_counts={"human": total, "ai": 0, "non_ai_automation": 0, "unknown": 0},
        lifecycle_exclusion_counts={"unknown_readiness": unknown},
    )


def assumptions() -> dict[str, object]:
    return {
        "review_effort": {
            "human": {"kind": "lognormal", "median_seconds": 900, "sigma": 0.4},
            "ai": {"kind": "constant", "seconds": 1200},
            "non_ai_automation": {"kind": "constant", "seconds": 600},
            "unknown": {"kind": "empirical", "seconds": [600, 900, 1800]},
        }
    }


def test_missing_required_assumptions_and_ambiguous_lognormal_fail_usefully() -> None:
    with pytest.raises(ValueError, match="required calibration assumptions.*review_effort"):
        load_assumptions({})

    ambiguous = assumptions()
    review_effort = ambiguous["review_effort"]
    assert isinstance(review_effort, dict)
    review_effort["human"] = {"kind": "lognormal", "mean_seconds": 900, "sigma": 0.4}
    with pytest.raises(ValueError, match="lognormal.*median_seconds.*log-space sigma"):
        load_assumptions(ambiguous)


@pytest.mark.parametrize("cohort", ["human", "ai", "non_ai_automation", "unknown"])
def test_missing_required_cohort_names_the_assumption_path(cohort: str) -> None:
    incomplete = assumptions()
    review_effort = incomplete["review_effort"]
    assert isinstance(review_effort, dict)
    del review_effort[cohort]

    with pytest.raises(ValueError, match=rf"required calibration assumptions missing: review_effort\.{cohort}"):
        load_assumptions(incomplete)


def test_calibration_rejects_coverage_from_another_dataset() -> None:
    other = coverage().model_copy(update={"dataset_content_hash": "b" * 64})

    with pytest.raises(ValueError, match="coverage does not match frozen feature source"):
        calibrate_model(features(), load_assumptions(assumptions()), other)


def test_model_preserves_parameter_provenance_and_readiness_policy() -> None:
    result = calibrate_model(
        features(policy="created_at_proxy"),
        load_assumptions(assumptions()),
        coverage(policy="created_at_proxy"),
        thresholds=CalibrationThresholds(min_usable_pull_requests=4, min_substantive_decisions=3),
    )

    assert result.model.readiness_policy == "created_at_proxy"
    assert result.calibration.readiness_policy == "created_at_proxy"
    assert result.model.evidence_status == "empirically_informed"
    assert result.model.arrival_templates == features().week_templates

    parameters = {parameter.name: parameter for parameter in result.model.parameters}
    assert parameters["arrival_week_templates"].basis == "derived"
    assert parameters["arrival_week_templates"].sample_count == 8
    assert parameters["first_substantive_review_elapsed"].basis == "derived"
    assert parameters["first_substantive_review_elapsed"].unit == "seconds"
    assert parameters["ready_to_merge_elapsed"].missingness_treatment == "completion_conditioned"
    assert parameters["review_effort.human"].basis == "assumed"
    assert parameters["review_effort.human"].value_specification == {
        "kind": "lognormal",
        "median_seconds": 900.0,
        "sigma": 0.4,
    }
    assert parameters["review_effort.human"].confidence_interval.value is None
    assert parameters["review_effort.human"].confidence_interval.reason == "not_declared"
    for parameter in parameters.values():
        assert parameter.unit
        assert parameter.sample_count >= 0
        assert parameter.missingness_treatment
        assert parameter.grouping_rule
        assert parameter.fallback_rule
        assert parameter.evidence_references


@pytest.mark.parametrize(
    "feature_kwargs,coverage_kwargs,expected",
    [
        ({"pulls": 3}, {}, "too_few_usable_pull_requests"),
        ({"decisions": 2}, {}, "too_few_substantive_decisions"),
        ({"weeks": 7}, {}, "insufficient_complete_weeks"),
        ({}, {"total": 5, "unknown": 2}, "excessive_unknown_readiness"),
    ],
)
def test_each_evidence_threshold_triggers_exploratory_only(
    feature_kwargs: dict[str, int], coverage_kwargs: dict[str, int], expected: str
) -> None:
    result = calibrate_model(
        features(
            pulls=feature_kwargs.get("pulls", 4),
            decisions=feature_kwargs.get("decisions", 3),
            weeks=feature_kwargs.get("weeks", 8),
        ),
        load_assumptions(assumptions()),
        coverage(total=coverage_kwargs.get("total", 5), unknown=coverage_kwargs.get("unknown", 1)),
        thresholds=CalibrationThresholds(
            min_usable_pull_requests=4,
            min_substantive_decisions=3,
            min_complete_weeks=8,
            max_unknown_readiness_fraction=0.25,
        ),
    )

    assert expected in result.model.evidence_flags
    assert result.model.evidence_status == "exploratory_only"


def test_decision_threshold_uses_the_mature_prevalence_denominator() -> None:
    many_recent_decisions = replace(
        features(pulls=30, decisions=30),
        requested_change_prevalence=RequestedChangePrevalence(0, 0, timedelta(days=7)),
    )

    result = calibrate_model(many_recent_decisions, load_assumptions(assumptions()), coverage(total=30, unknown=0))

    assert result.calibration.substantive_decisions == 0
    assert "too_few_substantive_decisions" in result.model.evidence_flags
    assert result.model.evidence_status == "exploratory_only"


def test_synthetic_and_incomplete_evidence_cannot_be_unqualified() -> None:
    synthetic = calibrate_model(
        features(pulls=30, decisions=20),
        load_assumptions(assumptions()),
        coverage(total=30, unknown=0).model_copy(update={"synthetic_data": True}),
    )
    assert synthetic.model.evidence_status == "synthetic_demonstration"
    assert "This calibration is empirically informed" not in render_model_card(synthetic)
    assert "This synthetic demonstration is not empirical evidence" in render_model_card(synthetic)

    incomplete_coverage = coverage(total=30, unknown=0)
    incomplete_coverage = incomplete_coverage.model_copy(
        update={"collection_status": {**incomplete_coverage.collection_status, "reviews": "partial"}}
    )
    incomplete = calibrate_model(features(pulls=30, decisions=20), load_assumptions(assumptions()), incomplete_coverage)
    assert "incomplete_source_collections" in incomplete.model.evidence_flags
    assert incomplete.model.evidence_status == "exploratory_only"


def test_model_card_renders_all_unavailable_quantities_as_null_with_reason() -> None:
    result = calibrate_model(
        features(),
        load_assumptions(assumptions()),
        coverage(),
        thresholds=CalibrationThresholds(min_usable_pull_requests=4, min_substantive_decisions=3),
    )

    card = render_model_card(result)

    assert "Readiness policy: `strict`" in card
    assert "Application version:" in card
    assert "Python version:" in card
    assert "Dependency versions:" in card
    assert "Seed: `null` (reason: `not_applicable_to_calibration`)" in card
    assert "RNG scheme: `null` (reason: `not_applicable_to_calibration`)" in card
    assert "Reviewer roster: `null` (reason: `downstream_simulation_input`)" in card
    assert "Initialization scheme: `null` (reason: `downstream_simulation_input`)" in card
    for name in ("defect_escape_rate", "security_risk_change", "policy_safety"):
        assert f"- `{name}`: `null` (reason: `unsupported_in_v0_1`)" in card
    assert "confidence interval: `null` (reason: `not_declared`)" in card
    normalized = re.sub(r"^- Python version: `[^`]+`$", "- Python version: `<runtime>`", card, flags=re.MULTILINE)
    assert hashlib.sha256(normalized.encode()).hexdigest() == (
        "9b5f81965175626cf54de22590a47b65760c76315375ff55e9fe554bfd70bbc6"
    )


def test_calibration_emits_model_record_and_model_card(tmp_path: Path) -> None:
    result = calibrate_model(
        features(),
        load_assumptions(assumptions()),
        coverage(),
        thresholds=CalibrationThresholds(min_usable_pull_requests=4, min_substantive_decisions=3),
    )

    write_calibration(result, tmp_path / "model")

    assert sorted(path.name for path in (tmp_path / "model").iterdir()) == [
        "calibration.json",
        "model-card.md",
        "model.json",
    ]
    model = json.loads((tmp_path / "model" / "model.json").read_text())
    record = json.loads((tmp_path / "model" / "calibration.json").read_text())
    assert model["readiness_policy"] == record["readiness_policy"] == "strict"
    assert model["parameters"][4]["confidence_interval"] == {"reason": "not_declared", "value": None}
    assert (tmp_path / "model" / "model-card.md").read_text() == render_model_card(result)

    with pytest.raises(ValueError, match="output directory must be empty or absent"):
        write_calibration(result, tmp_path / "model")
