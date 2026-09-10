from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.engine import Reviewer, run_fifo

pytestmark = pytest.mark.unit
START = datetime(2026, 1, 1, tzinfo=UTC)


def span(start: float, end: float) -> UTCInterval:
    return UTCInterval(START + timedelta(seconds=start), START + timedelta(seconds=end))


def pr(name: str, author: str = "author", ready: float = 0) -> PullRequest:
    return PullRequest(name, author, WorkOrigin.UNKNOWN, ready)


@pytest.mark.parametrize("reviewers,ends", [(1, [600, 1200]), (2, [600, 600])])
def test_hand_calculated_fifo(reviewers: int, ends: list[int]) -> None:
    result = run_fifo(
        (pr("b"), pr("a")),
        tuple(Reviewer(str(i), (span(0, 2000),)) for i in range(reviewers)),
        span=span(0, 2000),
        service_seconds=600,
    )
    assert [p.terminal_at for p in result.pull_requests] == ends
    assert sum(p.active_review_seconds for p in result.pull_requests) == 1200
    assert [p.queue_wait_seconds for p in result.pull_requests] == ([0, 600] if reviewers == 1 else [0, 0])


def test_pause_resume_same_reviewer_and_partial_horizon() -> None:
    reviewer = Reviewer("r", (span(0, 3600), span(86400, 93600)))
    result = run_fifo((pr("a"),), (reviewer,), span=span(0, 100000), service_seconds=7200)
    assert result.pull_requests[0].terminal_at == 90000
    assert result.pull_requests[0].active_review_seconds == 7200
    partial = run_fifo((pr("a"),), (reviewer,), span=span(0, 88000), service_seconds=7200)
    assert partial.pull_requests[0].censored
    assert partial.pull_requests[0].active_review_seconds == 5200
    assert partial.reviewers[0].duty_seconds == 5200


def test_paused_work_is_not_reassigned() -> None:
    result = run_fifo(
        (pr("a"), pr("b", ready=5)),
        (Reviewer("first", (span(0, 5), span(30, 50))), Reviewer("second", (span(5, 30),))),
        span=span(0, 60),
        service_seconds=10,
    )
    assert [p.terminal_at for p in result.pull_requests] == [35, 15]


def test_fifo_uses_arrival_before_identifier() -> None:
    result = run_fifo(
        (pr("a", ready=3), pr("z", ready=1)), (Reviewer("r", (span(10, 50),)),), span=span(0, 60), service_seconds=2.1
    )
    assert [p.terminal_at for p in result.pull_requests] == [16, 13]
    assert result.pull_requests[0].active_review_seconds == 3


def test_fractional_readiness_finishes_without_rescheduling_same_time() -> None:
    # A subprocess timeout makes a scheduler non-progress regression fail, not hang pytest.
    import subprocess
    import sys

    script = """
from tests.unit.simulation.engine_test import pr, span, Reviewer, run_fifo
result = run_fifo((pr('a', ready=0.3),), (Reviewer('r', (span(0, 10),)),),
                  span=span(0, 10), service_seconds=2)
assert result.pull_requests[0].terminal_at == 2.3
assert result.pull_requests[0].active_review_seconds == 2
"""
    subprocess.run([sys.executable, "-c", script], check=True, timeout=3)


@pytest.mark.parametrize("service", [0, -1, float("nan"), float("inf")])
def test_invalid_service(service: float) -> None:
    with pytest.raises(ValueError, match="constant service"):
        run_fifo((), (), span=span(0, 10), service_seconds=service)


def test_invalid_inputs() -> None:
    from dataclasses import replace

    with pytest.raises(ValueError, match="unique"):
        run_fifo((pr("a"), pr("a")), (), span=span(0, 10), service_seconds=1)
    with pytest.raises(ValueError, match="unique"):
        run_fifo((), (Reviewer("r", ()), Reviewer("r", ())), span=span(0, 10), service_seconds=1)
    for proposal in (pr("a", ready=-1), replace(pr("a"), abandonment_deadline=5)):
        with pytest.raises(ValueError, match="fresh READY"):
            run_fifo((proposal,), (), span=span(0, 10), service_seconds=1)
    with pytest.raises(ValueError, match="identifier"):
        Reviewer("", ())
    with pytest.raises(ValueError, match="sorted and disjoint"):
        Reviewer("r", (span(0, 10), span(5, 15)))


def test_absent_and_self_only_are_unresolved() -> None:
    for reviewer in (Reviewer("author", (span(0, 2000),)), Reviewer("other", ())):
        result = run_fifo((pr("a"),), (reviewer,), span=span(0, 2000), service_seconds=600)
        assert result.pull_requests[0].censored
        assert result.pull_requests[0].queue_wait_seconds == 2000
        assert result.pull_requests[0].active_review_seconds == 0
        assert result.limitations == ("no_eligible_reviewer:a",)


def test_eligibility_and_reviewer_ties_are_stable() -> None:
    reviewers = (Reviewer("b", (span(0, 2000),)), Reviewer("a", (span(0, 2000),)))
    prs = (pr("1", "a"), pr("2", "b"), pr("3"))
    result = run_fifo(prs, reviewers, span=span(0, 2000), service_seconds=600)
    assert result == run_fifo(tuple(reversed(prs)), tuple(reversed(reviewers)), span=span(0, 2000), service_seconds=600)
    assert [(p.pr_id, p.terminal_at) for p in result.pull_requests] == [("1", 600), ("2", 600), ("3", 1200)]
    assert [r.active_seconds for r in result.reviewers] == [1200, 600]


def test_ineligible_first_reviewer_does_not_block_later_reviewer() -> None:
    from dataclasses import replace

    proposal = replace(pr("a", "first"), revision=3, bypass_eligible=True, bypass_audited=True)
    result = run_fifo(
        (proposal,),
        (Reviewer("first", (span(0, 10),)), Reviewer("second", (span(0, 10),))),
        span=span(0, 10),
        service_seconds=2,
    )
    assert result.pull_requests[0].terminal_at == 2
    assert result.pull_requests[0].approved_revision == 3
    assert not result.pull_requests[0].review_bypassed
    assert [(r.reviewer_id, r.active_seconds) for r in result.reviewers] == [("first", 0), ("second", 2)]
    assert proposal.first_review_at is None


def test_duty_outside_run_and_before_readiness_is_not_capacity() -> None:
    result = run_fifo(
        (pr("a", ready=5),),
        (Reviewer("r", (span(-20, -10), span(2, 5), span(10, 20))),),
        span=span(0, 10),
        service_seconds=1,
    )
    assert result.reviewers[0].duty_seconds == 3
    assert result.limitations == ("no_eligible_reviewer:a",)
    assert result.pull_requests[0].censored
    assert result.boundaries[0].at == 0
    assert result.boundaries[-1].at == 10
    assert all(0 <= e.at <= 10 for e in result.boundaries)


def test_arrivals_shift_boundary_and_horizon_ties() -> None:
    result = run_fifo(
        (pr("a", ready=10), pr("b", ready=20), pr("outside", ready=50)),
        (Reviewer("r", (span(0, 20), span(30, 50))),),
        span=span(0, 50),
        service_seconds=10,
    )
    assert [(p.pr_id, p.terminal_at, p.censored) for p in result.pull_requests] == [("a", 20, False), ("b", 40, False)]
    tied = run_fifo((pr("a"),), (Reviewer("r", (span(0, 10),)),), span=span(0, 10), service_seconds=10)
    assert tied.pull_requests[0].censored
    assert tied.pull_requests[0].active_review_seconds == 10


@pytest.mark.property
@given(st.lists(st.integers(0, 150), max_size=15), st.integers(1, 30))
def test_conservation_times_waits_and_capacity(arrivals: list[int], service: int) -> None:
    result = run_fifo(
        tuple(pr(str(i), ready=t) for i, t in enumerate(arrivals)),
        (Reviewer("r", (span(0, 40), span(70, 120))),),
        span=span(0, 150),
        service_seconds=service,
    )
    assert [e.at for e in result.boundaries] == sorted({e.at for e in result.boundaries})
    for event in result.boundaries:
        assert event.arrivals == event.merges + event.unresolved + event.work_in_progress
    assert all(p.queue_wait_seconds >= 0 for p in result.pull_requests)
    assert 0 <= result.reviewers[0].active_seconds <= 90
    assert sum(p.active_review_seconds for p in result.pull_requests) == result.reviewers[0].active_seconds
