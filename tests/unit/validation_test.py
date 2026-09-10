"""Held-out descriptive validation and evidence gates."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import PullRequest, PullRequestState, TerminalReason, WorkOrigin
from merge_carlo.simulation.engine import FIFOResult, Reviewer
from merge_carlo.validation import (
    FrozenReplayModel,
    HeldOutEvidence,
    ObservedOutcomes,
    ReplayArrival,
    ReplayDuty,
    ReplayOutcomes,
    ValidationInput,
    ValidationThresholds,
    load_validation_evidence,
    render_validation_report,
    replay_held_out,
    run_validation,
    write_validation,
)

pytestmark = pytest.mark.unit


def evidence(*, observed_count: int = 40, reviewed: float = 0.75, merged: float = 0.6) -> HeldOutEvidence:
    thresholds = ValidationThresholds(
        min_mature_pull_requests=20,
        min_replications=3,
        reviewed_share_tolerance=0.1,
        merged_share_tolerance=0.1,
        first_review_median_tolerance_seconds=1800,
        weekly_merges_tolerance=1.0,
        initialization_backlog_tolerance=2.0,
    )
    observed = ObservedOutcomes(
        reviewed_within_48_hours_successes=round(reviewed * observed_count),
        reviewed_mature_pull_requests=observed_count,
        merged_within_7_days_successes=round(merged * observed_count),
        merged_mature_pull_requests=observed_count,
        first_review_elapsed_seconds=(3200.0, 3600.0, 4000.0),
        weekly_merge_counts=(6, 8, 7, 7),
        initial_backlog=4,
    )
    replications = tuple(
        ReplayOutcomes(
            reviewed_within_48_hours_successes=round(value * observed_count),
            reviewed_mature_pull_requests=observed_count,
            merged_within_7_days_successes=round((value - 0.15) * observed_count),
            merged_mature_pull_requests=observed_count,
            first_review_median_seconds=latency,
            first_review_completions=30,
            weekly_merge_counts=(6, 7, 8, 7),
            initial_backlog=backlog,
        )
        for value, latency, backlog in ((0.725, 3500.0, 4), (0.775, 3700.0, 5), (0.75, 3600.0, 4))
    )
    return HeldOutEvidence(
        model_version="fifo-v0.1",
        dataset_content_hash="a" * 64,
        fitting_interval_start=datetime(2025, 10, 1, tzinfo=UTC),
        training_cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        validation_interval_start=datetime(2026, 1, 1, tzinfo=UTC),
        validation_interval_end=datetime(2026, 2, 1, tzinfo=UTC),
        observed=observed,
        replay_replications=replications,
        thresholds=thresholds,
    )


def replay_input() -> ValidationInput:
    return ValidationInput(
        dataset_content_hash="a" * 64,
        fitting_interval_start=datetime(2025, 10, 1, tzinfo=UTC),
        training_cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        validation_interval_start=datetime(2026, 1, 1, tzinfo=UTC),
        validation_interval_end=datetime(2026, 2, 1, tzinfo=UTC),
        observed=ObservedOutcomes(1, 1, 1, 1, (1.0,), (1, 0, 0, 0, 0), 0),
        model=FrozenReplayModel("fifo-v0.1", "UTC", 1.0),
        arrivals=(ReplayArrival("pr-1", "author", WorkOrigin.HUMAN, datetime(2026, 1, 2, tzinfo=UTC)),),
        reviewer_duty=(ReplayDuty("reviewer", datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)),),
        root_seed=7,
        replications=3,
        thresholds=ValidationThresholds(min_mature_pull_requests=1, min_replications=3),
    )


def test_pass_outputs_exact_values_cohorts_variability_and_cautions(tmp_path: Path) -> None:
    result = run_validation(evidence())

    assert result.status == "pass"
    reviewed = next(gate for gate in result.gates if gate.metric == "reviewed_within_48_hours_share")
    assert reviewed.observed.value == 0.75
    assert reviewed.observed.sample_size == 40
    assert reviewed.observed.low is not None and reviewed.observed.high is not None
    assert reviewed.simulated.value == 0.75
    assert reviewed.simulated.sample_size == 3
    assert reviewed.observed_cohort_size == 40
    assert reviewed.simulated_cohort_sizes == (40, 40, 40)
    assert (reviewed.simulated.low, reviewed.simulated.high) == pytest.approx((0.7275, 0.7725))
    assert reviewed.passed is True
    assert result.absolute_backlog_forecast_supported is True
    assert result.unsupported["policy_safety"].value is None

    report = render_validation_report(result)
    assert "held-out descriptive pass" in report
    assert "0.75 [0.7275, 0.7725]; n=3" in report
    assert "cohorts=40,40,40" in report
    assert "does not establish causal validation" in report
    assert "does not establish that auto-approval is safe" in report

    write_validation(result, tmp_path / "validation")
    payload = json.loads((tmp_path / "validation" / "validation.json").read_text())
    assert payload["gates"][0]["observed"]["sample_size"] > 0
    assert (tmp_path / "validation" / "report.md").read_text() == report


def test_failed_tolerance_and_material_initialization_discrepancy_fail_declared_gates() -> None:
    sample = evidence(reviewed=0.95, merged=0.85)
    replications = tuple(replace(row, initial_backlog=10) for row in sample.replay_replications)

    result = run_validation(replace(sample, replay_replications=replications))

    assert result.status == "fail"
    failed = {gate.metric for gate in result.gates if gate.passed is False}
    assert failed == {
        "reviewed_within_48_hours_share",
        "merged_within_7_days_share",
        "initialization_backlog",
    }
    assert result.initialization_discrepancy.value == 6.0
    assert result.absolute_backlog_forecast_supported is False
    assert "Absolute backlog forecasting: not supported" in render_validation_report(result)


def test_small_mature_cohort_is_insufficient_evidence_not_fail() -> None:
    result = run_validation(evidence(observed_count=10))

    assert result.status == "insufficient_evidence"
    assert result.evidence_flags == ("too_few_mature_pull_requests",)
    assert all(gate.passed is None for gate in result.gates)
    assert "insufficient_evidence" in render_validation_report(result)


def test_undefined_simulated_completion_metric_is_insufficient_evidence() -> None:
    sample = evidence()
    replications = tuple(
        replace(row, first_review_median_seconds=None, first_review_completions=0) for row in sample.replay_replications
    )

    result = run_validation(replace(sample, replay_replications=replications))

    assert result.status == "insufficient_evidence"
    assert "no_simulated_first_review_completions" in result.evidence_flags
    assert all(gate.passed is None for gate in result.gates)


def test_one_defined_completion_replication_is_insufficient_evidence() -> None:
    sample = evidence()
    replications = tuple(
        row if index == 0 else replace(row, first_review_median_seconds=None, first_review_completions=0)
        for index, row in enumerate(sample.replay_replications)
    )

    result = run_validation(replace(sample, replay_replications=replications))

    assert result.status == "insufficient_evidence"
    assert "too_few_defined_first_review_replications" in result.evidence_flags


def test_empty_observed_completion_cohort_is_insufficient_evidence() -> None:
    sample = evidence()
    observed = replace(sample.observed, first_review_elapsed_seconds=())

    result = run_validation(replace(sample, observed=observed))

    assert result.status == "insufficient_evidence"
    assert "no_observed_first_review_completions" in result.evidence_flags


def test_distinct_horizon_cohorts_and_skewed_weekly_counts_use_declared_denominators() -> None:
    sample = evidence()
    observed = replace(
        sample.observed,
        reviewed_within_48_hours_successes=30,
        reviewed_mature_pull_requests=40,
        merged_within_7_days_successes=15,
        merged_mature_pull_requests=30,
        weekly_merge_counts=(0, 0, 100),
    )
    replications = tuple(replace(row, weekly_merge_counts=(0, 0, 100)) for row in sample.replay_replications)

    result = run_validation(replace(sample, observed=observed, replay_replications=replications))

    reviewed, merged, _, weekly, _ = result.gates
    assert reviewed.observed.value == 0.75
    assert merged.observed.value == 0.5
    assert (reviewed.observed_cohort_size, merged.observed_cohort_size) == (40, 30)
    assert weekly.absolute_error == 0


def test_overlap_is_rejected_unless_explicitly_in_sample() -> None:
    sample = evidence()
    overlapping = replace(sample, validation_interval_start=datetime(2025, 12, 15, tzinfo=UTC))

    with pytest.raises(ValueError, match="overlaps parameter fitting"):
        run_validation(overlapping)

    diagnostic = run_validation(replace(overlapping, in_sample_diagnostic=True))
    assert diagnostic.protocol == "in_sample_diagnostic"
    assert "not held-out evidence" in render_validation_report(diagnostic)


def test_versioned_input_rejects_unknown_keys(tmp_path: Path) -> None:
    payload = TypeAdapter(ValidationInput).dump_python(replay_input(), mode="json")
    payload.update(schema_version=1, unexpected="ignored would weaken the evidence contract")
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid validation evidence"):
        load_validation_evidence(source)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("thresholds", "min_replications"), "3"),
        (("observed", "reviewed_mature_pull_requests"), "40"),
        (("replications",), "3"),
        (("in_sample_diagnostic",), "false"),
        (("validation_interval_start",), 1_767_225_600),
    ],
)
def test_versioned_input_rejects_scalar_type_coercion(
    tmp_path: Path, path: tuple[str | int, ...], value: object
) -> None:
    payload = TypeAdapter(ValidationInput).dump_python(replay_input(), mode="json")
    payload["schema_version"] = 1
    target: object = payload
    for part in path[:-1]:
        assert isinstance(target, (dict, list))
        target = target[part]  # type: ignore[index]
    assert isinstance(target, (dict, list))
    target[path[-1]] = value  # type: ignore[index]
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid validation evidence"):
        load_validation_evidence(source)


def test_report_escapes_untrusted_model_version() -> None:
    result = run_validation(replace(evidence(), model_version="bad`\n# forged [link](https://example.com) |"))

    report = render_validation_report(result)

    assert "\n# forged" not in report
    assert "[link](" not in report


def test_loader_replays_exact_arrivals_and_binds_model_and_arrival_content(tmp_path: Path) -> None:
    payload = TypeAdapter(ValidationInput).dump_python(replay_input(), mode="json")
    payload["schema_version"] = 1
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    replayed = load_validation_evidence(source)
    result = run_validation(replayed)

    assert replayed.replay_replications[0].reviewed_within_48_hours_successes == 1
    assert replayed.replay_replications[0].merged_within_7_days_successes == 1
    assert result.status == "pass"
    assert result.model_content_hash != result.replay_arrivals_content_hash
    assert result.model_content_hash in render_validation_report(result)

    changed = replace(
        replay_input(),
        arrivals=(ReplayArrival("pr-1", "author", WorkOrigin.HUMAN, datetime(2026, 1, 3, tzinfo=UTC)),),
    )
    changed_payload = TypeAdapter(ValidationInput).dump_python(changed, mode="json")
    changed_payload["schema_version"] = 1
    changed_source = tmp_path / "changed.json"
    changed_source.write_text(json.dumps(changed_payload), encoding="utf-8")
    changed_replay = load_validation_evidence(changed_source)
    assert changed_replay.model_content_hash == replayed.model_content_hash
    assert changed_replay.replay_arrivals_content_hash != replayed.replay_arrivals_content_hash


def test_replay_passes_the_frozen_contract_and_derives_fixed_horizon_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = replace(
        replay_input(),
        model=FrozenReplayModel(
            "fifo-v0.1",
            "UTC",
            17.0,
            verification_seconds=2.0,
            author_response_seconds=3.0,
            verification_failure_probability=0.1,
            first_change_probability=0.2,
            repeat_change_probability=0.3,
            max_review_visits=4,
            max_verification_attempts=5,
            coordination_seconds=6.0,
        ),
        arrivals=(
            ReplayArrival("pr-2", "author-2", WorkOrigin.AI, datetime(2026, 1, 30, tzinfo=UTC)),
            ReplayArrival("pr-1", "author-1", WorkOrigin.HUMAN, datetime(2026, 1, 1, tzinfo=UTC)),
        ),
        reviewer_duty=(
            ReplayDuty("z-reviewer", datetime(2026, 1, 8, tzinfo=UTC), datetime(2026, 1, 9, tzinfo=UTC)),
            ReplayDuty("a-reviewer", datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)),
            ReplayDuty("z-reviewer", datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)),
        ),
        root_seed=0,
        replications=3,
    )
    span_seconds = 31 * 86400
    pulls = (
        PullRequest(
            "within-both",
            "author",
            WorkOrigin.HUMAN,
            0,
            state=PullRequestState.MERGED,
            first_review_at=48 * 3600,
            terminal_at=7 * 86400,
            terminal_reason=TerminalReason.MERGED,
            review_visit_count=1,
            verification_count=1,
            verified_revision=1,
            approved_revision=1,
        ),
        PullRequest(
            "review-boundary",
            "author",
            WorkOrigin.AI,
            span_seconds - 48 * 3600,
            first_review_at=span_seconds,
            _last_transition_at=span_seconds,
        ),
        PullRequest(
            "review-immature",
            "author",
            WorkOrigin.UNKNOWN,
            span_seconds - 48 * 3600 + 1,
        ),
        PullRequest(
            "merge-boundary",
            "author",
            WorkOrigin.NON_AI_AUTOMATION,
            span_seconds - 7 * 86400 - 1,
            state=PullRequestState.MERGED,
            first_review_at=span_seconds - 7 * 86400 + 10,
            terminal_at=span_seconds - 1,
            terminal_reason=TerminalReason.MERGED,
            review_visit_count=1,
            verification_count=1,
            verified_revision=1,
            approved_revision=1,
        ),
        PullRequest(
            "merge-immature",
            "author",
            WorkOrigin.HUMAN,
            span_seconds - 7 * 86400 + 1,
        ),
    )
    calls: list[tuple[tuple[PullRequest, ...], tuple[Reviewer, ...], dict[str, object]]] = []

    def fake_run_fifo(
        proposals: tuple[PullRequest, ...], reviewers: tuple[Reviewer, ...], **kwargs: object
    ) -> FIFOResult:
        calls.append((proposals, reviewers, kwargs))
        return FIFOResult(pulls, (), (), (), engine_truncated=kwargs["replication"] == 0)

    monkeypatch.setattr("merge_carlo.validation.run_fifo", fake_run_fifo)

    replayed = replay_held_out(request)

    assert len(calls) == 3
    proposals, reviewers, options = calls[2]
    assert [(pull.pr_id, pull.author_id, pull.origin, pull.ready_at) for pull in proposals] == [
        ("pr-2", "author-2", WorkOrigin.AI, 29 * 86400.0),
        ("pr-1", "author-1", WorkOrigin.HUMAN, 0.0),
    ]
    assert [(reviewer.reviewer_id, [(d.start, d.end) for d in reviewer.duty]) for reviewer in reviewers] == [
        (
            "a-reviewer",
            [(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC))],
        ),
        (
            "z-reviewer",
            [
                (datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)),
                (datetime(2026, 1, 8, tzinfo=UTC), datetime(2026, 1, 9, tzinfo=UTC)),
            ],
        ),
    ]
    span = options["span"]
    assert isinstance(span, UTCInterval)
    assert span.start == datetime(2026, 1, 1, tzinfo=UTC)
    assert span.end == datetime(2026, 2, 1, tzinfo=UTC)
    assert options["service_seconds"] == 17.0
    assert options["loops"] == request.model.loops()
    assert options["coordination_seconds"] == 6.0
    assert options["root_seed"] == 0
    assert [call[2]["replication"] for call in calls] == [0, 1, 2]
    assert replayed.replay_replications == (
        ReplayOutcomes(3, 4, 2, 2, 172800.0, 3, (0, 1, 0, 0, 1), 0),
        ReplayOutcomes(3, 4, 2, 2, 172800.0, 3, (0, 1, 0, 0, 1), 0),
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: replace(value, model=FrozenReplayModel("", "UTC", 1.0)), "model version must be nonempty"),
        (lambda value: replace(value, dataset_content_hash="g" * 64), "invalid dataset content hash"),
        (lambda value: replace(value, root_seed=-1), "root seed must be a nonnegative integer"),
        (lambda value: replace(value, replications=0), "replications must be between one and 10000"),
        (lambda value: replace(value, replications=10_001), "replications must be between one and 10000"),
        (lambda value: replace(value, arrivals=()), "replay arrivals must be nonempty with unique identifiers"),
        (
            lambda value: replace(
                value,
                arrivals=(
                    ReplayArrival("pr-1", "a", WorkOrigin.HUMAN, datetime(2026, 1, 1, tzinfo=UTC)),
                    ReplayArrival("pr-1", "b", WorkOrigin.AI, datetime(2026, 1, 2, tzinfo=UTC)),
                ),
            ),
            "replay arrivals must be nonempty with unique identifiers",
        ),
        (
            lambda value: replace(
                value,
                arrivals=(ReplayArrival("pr-1", "a", WorkOrigin.HUMAN, datetime(2026, 2, 1, tzinfo=UTC)),),
            ),
            "replay arrivals must fall within the validation interval",
        ),
        (
            lambda value: replace(
                value,
                reviewer_duty=(ReplayDuty("reviewer", datetime(2026, 1, 1), datetime(2026, 1, 2, tzinfo=UTC)),),
            ),
            "reviewer duty must be timezone aware",
        ),
    ],
)
def test_replay_rejects_invalid_frozen_inputs(
    change: Callable[[ValidationInput], ValidationInput], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replay_held_out(change(replay_input()))


def test_replay_accepts_boundaries_and_normalizes_timezone() -> None:
    offset = timezone(timedelta(hours=5))
    request = replace(
        replay_input(),
        validation_interval_start=datetime(2026, 1, 1, 5, tzinfo=offset),
        validation_interval_end=datetime(2026, 2, 1, 5, tzinfo=offset),
        arrivals=(ReplayArrival("pr-1", "author", WorkOrigin.HUMAN, datetime(2026, 1, 1, 5, tzinfo=offset)),),
        root_seed=0,
        replications=1,
    )

    result = replay_held_out(request)

    assert len(result.replay_replications) == 1
    assert result.in_sample_diagnostic is False


def test_report_is_the_complete_deterministic_evidence_record() -> None:
    result = run_validation(evidence())

    report = render_validation_report(result)

    assert (
        hashlib.sha256(report.encode()).hexdigest()
        == "7830fe7f9fd21ec62b3c160130821c5b1722b02da8a06327434e0ae94a35801c"
    )


def test_write_validation_rejects_unsafe_destinations_and_replaces_empty_directory(tmp_path: Path) -> None:
    result = run_validation(evidence())
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep").write_text("existing", encoding="utf-8")
    plain_file = tmp_path / "plain-file"
    plain_file.write_text("existing", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "link"
    symlink.symlink_to(target, target_is_directory=True)

    for invalid in (occupied, plain_file, symlink):
        with pytest.raises(ValueError, match="output directory must be empty or absent"):
            write_validation(result, invalid)

    nested = tmp_path / "new" / "empty"
    nested.mkdir(parents=True)
    write_validation(result, nested)

    assert sorted(path.name for path in nested.iterdir()) == ["report.md", "validation.json"]
