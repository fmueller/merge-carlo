"""Hand-computed measurement ledgers, including carry-in and censored work."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.engine import Abandonment, ReviewBypass, Reviewer, RevisionLoops, run_fifo
from merge_carlo.simulation.metrics import Metric, MetricWindow, summarize_metrics

pytestmark = pytest.mark.unit
START = datetime(2026, 1, 1, tzinfo=UTC)


def test_hand_computed_window() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    result = run_fifo(
        tuple(PullRequest(str(i), "a", WorkOrigin.HUMAN, t) for i, t in enumerate((0, 6, 7, 19, 20))),
        (Reviewer("r", (span,)),),
        span=span,
        service_seconds=8,
        measurement=MetricWindow(5, 20, 10, 1),
    )
    assert result.metrics is not None
    all_work, cohort = result.metrics.all_work, result.metrics.new_ready
    assert (all_work.arrivals, all_work.merges, all_work.abandonments) == (3, 2, 0)
    assert (all_work.wip_start, all_work.wip_end) == (1, 2)
    assert (cohort.wip_start, cohort.wip_end, cohort.merges) == (0, 2, 1)
    assert all_work.queue_peak == 2
    assert all_work.queue_time_average == pytest.approx(12 / 15)
    assert all_work.backlog_exceeded == 1
    assert all_work.queue_wait_seconds == 12
    assert all_work.review_utilization == Metric(1)
    assert cohort.review_utilization == Metric(12 / 15)
    assert all_work.first_review_median == Metric(1)
    assert all_work.first_review_p95.value == pytest.approx(1.9)
    assert cohort.first_review_median == Metric(2)
    assert all_work.ready_to_merge_median == Metric(9)
    assert all_work.ready_to_merge_p95.value == pytest.approx(9.9)
    assert (cohort.reviewed.total, cohort.reviewed.eligible, cohort.reviewed.excluded) == (3, 2, 1)
    assert cohort.reviewed.share == Metric(0.5)
    assert cohort.merged.share == Metric(0.5)
    assert all_work.unresolved_share == Metric(0.5)
    assert cohort.unresolved_share == Metric(2 / 3)
    assert all_work.requested_changes == all_work.unreviewed_merges == 0


def test_empty_and_no_completed_review_are_not_zero_latency() -> None:
    span = UTCInterval(START, START + timedelta(seconds=10))
    for proposals in ((), (PullRequest("p", "a", WorkOrigin.UNKNOWN, 9),)):
        result = run_fifo(proposals, (), span=span, service_seconds=3, measurement=MetricWindow(0, 10, 2, 0))
        assert result.metrics is not None
        metrics = result.metrics.new_ready
        assert metrics.first_review_median == Metric(None, "no_completed_reviews")
        assert metrics.first_review_p95 == Metric(None, "no_completed_reviews")
        assert metrics.ready_to_merge_median == Metric(None, "no_merges")
        assert metrics.ready_to_merge_p95 == Metric(None, "no_merges")
        assert metrics.review_utilization == Metric(None, "no_declared_review_capacity")
        assert metrics.reviewed.share == Metric(None, "no_eligible_cohort")
        assert metrics.queue_wait_seconds == len(proposals)
        assert metrics.unresolved_share == (Metric(1) if proposals else Metric(None, "no_eligible_cohort"))


def test_summary_uses_run_statistics_not_pooled_prs() -> None:
    summary = summarize_metrics((Metric(1), Metric(11), Metric(None, "no_completed_reviews")))
    assert summary.median == Metric(6)
    assert summary.low.value == pytest.approx(1.5)
    assert summary.high.value == pytest.approx(10.5)
    assert (summary.total, summary.defined, summary.excluded) == (3, 2, 1)
    assert summarize_metrics(()).median == Metric(None, "no_defined_replications")


def test_boundary_outcomes_and_bypass_do_not_count_as_review() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    result = run_fifo(
        tuple(PullRequest(str(i), "a", WorkOrigin.AI, t) for i, t in enumerate((0, 3, 5, 17, 20))),
        (),
        span=span,
        service_seconds=2,
        bypass=ReviewBypass(1, 0),
        coordination_seconds=2,
        measurement=MetricWindow(5, 20, 3, 0),
    )
    assert result.metrics is not None
    a, c = result.metrics.all_work, result.metrics.new_ready
    assert (a.wip_start, a.arrivals, a.merges, a.wip_end) == (1, 2, 3, 0)
    assert (c.wip_start, c.arrivals, c.merges, c.wip_end) == (0, 2, 2, 0)
    assert (a.unreviewed_merges, c.unreviewed_merges) == (3, 2)
    assert a.first_review_p95 == Metric(None, "no_completed_reviews")
    assert a.reviewed.share == Metric(0)
    assert a.merged.share == Metric(1)
    assert (c.merged.total, c.merged.eligible, c.merged.excluded) == (2, 1, 1)
    assert a.backlog_exceeded == a.queue_peak == a.queue_wait_seconds == 0


def test_abandonment_cancels_service_but_preserves_window_queue_wait() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    result = run_fifo(
        tuple(PullRequest(str(i), "a", WorkOrigin.HUMAN, t) for i, t in enumerate((0, 5, 7, 19))),
        (Reviewer("r", (span,)),),
        span=span,
        service_seconds=10,
        abandonment=Abandonment(1, (5,)),
        measurement=MetricWindow(5, 20, 5, 1),
    )
    assert result.metrics is not None
    a, c = result.metrics.all_work, result.metrics.new_ready
    assert (a.wip_start, a.arrivals, a.abandonments, a.merges, a.wip_end) == (1, 3, 3, 0, 1)
    assert c.abandonments == 2
    assert a.first_review_median == Metric(None, "no_completed_reviews")
    assert a.review_utilization.value == pytest.approx(8 / 15)
    assert a.queue_wait_seconds == 3
    assert a.queue_peak == 1
    assert a.backlog_exceeded == 0  # equality does not exceed
    assert c.reviewed.share == Metric(0)
    assert c.merged.share == Metric(0)
    assert c.unresolved_share == Metric(1 / 3)


def test_repeat_reviews_count_changes_not_duplicate_first_latencies() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    result = run_fifo(
        (PullRequest("carry", "a", WorkOrigin.HUMAN, 0), PullRequest("new", "a", WorkOrigin.HUMAN, 5)),
        (Reviewer("r", (span,)),),
        span=span,
        service_seconds=2,
        loops=RevisionLoops(first_change_probability=1, repeat_change_probability=1),
        measurement=MetricWindow(4, 20, 3, 0),
    )
    assert result.metrics is not None
    a, c = result.metrics.all_work, result.metrics.new_ready
    assert (a.requested_changes, c.requested_changes) == (8, 3)
    # New work arrives at 5, starts at 6 and completes at its deadline 8.
    assert a.first_review_median == c.first_review_median == Metric(1)
    assert a.reviewed.share == Metric(1)
    assert c.reviewed.share == Metric(1)
    assert a.merged.share == Metric(0)
    assert a.unresolved_share == Metric(1)


def test_exact_start_arrival_contributes_queue_service_and_changes() -> None:
    span = UTCInterval(START, START + timedelta(seconds=15))
    duty = (UTCInterval(START + timedelta(seconds=7), span.end),)
    result = run_fifo(
        (PullRequest("p", "a", WorkOrigin.HUMAN, 5),),
        (Reviewer("r", duty),),
        span=span,
        service_seconds=3,
        loops=RevisionLoops(first_change_probability=1),
        measurement=MetricWindow(5, 15, 5, 0),
    )
    assert result.metrics is not None
    assert result.metrics.all_work == result.metrics.new_ready
    metrics = result.metrics.new_ready
    assert metrics.requested_changes == 1
    assert metrics.queue_wait_seconds == 2
    assert metrics.review_utilization == Metric(6 / 8)
    assert metrics.reviewed.share == Metric(1)
    assert metrics.merged.share == Metric(0)


def test_off_duty_service_and_fractional_window_are_clipped() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    duty = (
        UTCInterval(START, START + timedelta(seconds=4)),
        UTCInterval(START + timedelta(seconds=10), START + timedelta(seconds=14)),
    )
    result = run_fifo(
        (PullRequest("p", "a", WorkOrigin.HUMAN, 1),),
        (Reviewer("r", duty), Reviewer("idle", (span,))),
        span=span,
        service_seconds=30,
        measurement=MetricWindow(3.5, 20, 4, 0),
    )
    assert result.metrics is not None
    # 'idle' sorts first and handles the PR throughout; r contributes idle duty.
    assert result.metrics.all_work.review_utilization.value == pytest.approx(16.5 / 21)
    assert result.metrics.new_ready.review_utilization == Metric(0)
    assert result.metrics.all_work.first_review_median == Metric(None, "no_completed_reviews")
    paused = run_fifo(
        (PullRequest("p", "a", WorkOrigin.HUMAN, 1),),
        (Reviewer("r", duty),),
        span=span,
        service_seconds=30,
        measurement=MetricWindow(3.5, 20, 4, 0),
    )
    assert paused.metrics is not None
    assert paused.metrics.all_work.review_utilization == Metric(1)


@pytest.mark.parametrize(
    "window",
    [
        (-1, 20, 2, 0),
        (20, 20, 2, 0),
        (21, 20, 2, 0),
        (0, 20, 0, 0),
        (0, 20, -1, 0),
        (0, 20, 2, -1),
        (0, 20, 2, True),
        (float("nan"), 20, 2, 0),
        (0, float("inf"), 2, 0),
        (0, 20, float("nan"), 0),
    ],
)
def test_invalid_window(window: tuple[float, float, float, int]) -> None:
    with pytest.raises(ValueError):
        MetricWindow(*window)


def test_measurement_requires_run_end_and_truncated_metrics_are_unusable() -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    with pytest.raises(ValueError, match="measurement end"):
        run_fifo((), (), span=span, service_seconds=2, measurement=MetricWindow(0, 19, 2, 0))
    result = run_fifo(
        (PullRequest("p", "a", WorkOrigin.HUMAN, 0),),
        (Reviewer("r", (span,)),),
        span=span,
        service_seconds=2,
        loops=RevisionLoops(first_change_probability=1, max_review_visits=1),
        measurement=MetricWindow(0, 20, 2, 0),
    )
    assert result.engine_truncated
    assert result.metrics is None


@pytest.mark.property
@given(st.lists(st.integers(0, 20), max_size=15), st.integers(0, 19), st.integers(1, 10), st.booleans())
def test_conservation(arrivals: list[int], start: int, service: int, abandon: bool) -> None:
    span = UTCInterval(START, START + timedelta(seconds=20))
    result = run_fifo(
        tuple(PullRequest(str(i), "a", WorkOrigin.HUMAN, t) for i, t in enumerate(arrivals)),
        (Reviewer("r", (span,)),),
        span=span,
        service_seconds=service,
        abandonment=Abandonment(0.5, (2, 7)) if abandon else None,
        measurement=MetricWindow(start, 20, 3, 2),
    )
    assert result.metrics is not None
    for metrics in (result.metrics.all_work, result.metrics.new_ready):
        assert metrics.wip_end == metrics.wip_start + metrics.arrivals - metrics.merges - metrics.abandonments
