from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.engine import Reviewer, RevisionLoops, run_fifo, summarize_replications

pytestmark = pytest.mark.unit
START = datetime(2026, 1, 1, tzinfo=UTC)


def span(start: float, end: float) -> UTCInterval:
    return UTCInterval(START + timedelta(seconds=start), START + timedelta(seconds=end))


def pr(name: str, author: str = "author", ready: float = 0) -> PullRequest:
    return PullRequest(name, author, WorkOrigin.UNKNOWN, ready)


def test_first_changes_then_approval_reverifies_and_counts_all_service() -> None:
    result = run_fifo(
        (pr("a"), pr("b")),
        (Reviewer("r", (span(0, 100),)),),
        span=span(0, 100),
        service_seconds=3,
        loops=RevisionLoops(verification_seconds=2, author_response_seconds=5, first_change_probability=1),
    )
    assert [
        (p.revision, p.review_visit_count, p.requested_change_count, p.verification_count) for p in result.pull_requests
    ] == [(2, 2, 1, 2), (2, 2, 1, 2)]
    assert [p.terminal_at for p in result.pull_requests] == [15, 18]
    assert [p.active_review_seconds for p in result.pull_requests] == [6, 6]
    assert [p.queue_wait_seconds for p in result.pull_requests] == [0, 3]
    assert result.reviewers[0].active_seconds == 12
    assert all(p.approved_revision == p.verified_revision == 2 for p in result.pull_requests)
    assert not result.engine_truncated


def test_verification_failure_then_pass_uses_revision_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from numpy.random import Generator

    calls: list[tuple[int, int, tuple[str | int, ...]]] = []

    class Draw:
        def __init__(self, value: float) -> None:
            self.value = value

        def random(self) -> float:
            return self.value

    def stream(seed: int, replication: int, *key: str | int) -> Generator:
        from typing import cast

        calls.append((seed, replication, key))
        return cast(Generator, Draw(0.2 if key == ("a", 1, "verification") else 0.8))

    monkeypatch.setattr("merge_carlo.simulation.engine.random_stream", stream)
    result = run_fifo(
        (pr("a"),),
        (Reviewer("r", (span(0, 100),)),),
        span=span(0, 100),
        service_seconds=3,
        loops=RevisionLoops(verification_seconds=7, author_response_seconds=11, verification_failure_probability=0.5),
        root_seed=23,
        replication=4,
    )
    p = result.pull_requests[0]
    assert (p.revision, p.verification_count, p.review_visit_count, p.first_review_at, p.terminal_at) == (
        2,
        2,
        1,
        25,
        28,
    )
    assert (p.active_review_seconds, p.queue_wait_seconds, p.requested_change_count) == (3, 0, 0)
    assert calls == [
        (23, 4, ("a", 1, "verification")),
        (23, 4, ("a", 2, "verification")),
        (23, 4, ("a", 1, "requested-change")),
    ]


@pytest.mark.parametrize("first,repeat,visits,truncated", [(0, 1, 1, False), (1, 0, 2, False), (1, 1, 2, True)])
def test_separate_visit_probabilities_and_inclusive_limit(
    first: float, repeat: float, visits: int, truncated: bool
) -> None:
    result = run_fifo(
        (pr("a"),),
        (Reviewer("r", (span(0, 100),)),),
        span=span(0, 100),
        service_seconds=2,
        loops=RevisionLoops(first_change_probability=first, repeat_change_probability=repeat, max_review_visits=2),
    )
    p = result.pull_requests[0]
    assert p.review_visit_count == visits
    assert result.engine_truncated is truncated
    assert p.terminal is not truncated
    if truncated:
        assert p.terminal_reason is None
        assert p.active_review_seconds == 4


def test_attempt_limit_stops_zero_delay_failure_loop_without_abandonment() -> None:
    result = run_fifo(
        (pr("a"),),
        (),
        span=span(0, 100),
        service_seconds=1,
        loops=RevisionLoops(verification_failure_probability=1, max_verification_attempts=3),
    )
    p = result.pull_requests[0]
    assert result.engine_truncated
    assert (p.revision, p.verification_count, p.review_visit_count) == (3, 3, 0)
    assert not p.terminal and not p.censored
    assert result.boundaries[-1].at == 0


def test_truncated_runs_are_excluded_and_disable_ranking() -> None:
    from dataclasses import replace

    good = run_fifo((pr("a"),), (Reviewer("r", (span(0, 100),)),), span=span(0, 100), service_seconds=1)
    bad = run_fifo(
        (pr("a"), pr("b", ready=2)),
        (Reviewer("r", (span(0, 100),)),),
        span=span(0, 100),
        service_seconds=1,
        loops=RevisionLoops(first_change_probability=1, max_review_visits=1),
    )
    summary = summarize_replications((good, bad))
    assert (summary.completed_replications, summary.engine_truncated_count) == (1, 1)
    assert (summary.merged, summary.unresolved) == (1, 0)
    assert summary.comparison_incomplete and not summary.policy_ranking_enabled
    empty = summarize_replications((bad,))
    assert empty.merged is None and empty.unresolved is None
    assert not empty.policy_ranking_enabled
    complete = summarize_replications((good,))
    assert not complete.comparison_incomplete and complete.policy_ranking_enabled
    assert summarize_replications(()).comparison_incomplete
    unresolved = run_fifo((pr("c"),), (), span=span(0, 100), service_seconds=1)
    # A truncated diagnostic can contain earlier merges: none may leak into counts.
    earlier_merge = replace(bad, pull_requests=good.pull_requests + bad.pull_requests)
    mixed = summarize_replications((good, unresolved, earlier_merge))
    assert (mixed.completed_replications, mixed.engine_truncated_count, mixed.merged, mixed.unresolved) == (2, 1, 1, 1)


@pytest.mark.parametrize("probability", [0.0, 0.5])
def test_probability_threshold_is_exclusive_and_random_defaults_are_zero(
    probability: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typing import cast

    from numpy.random import Generator

    calls: list[tuple[int, int]] = []

    class Draw:
        def random(self) -> float:
            return probability

    def stream(seed: int, replication: int, *key: str | int) -> Generator:
        calls.append((seed, replication))
        return cast(Generator, Draw())

    monkeypatch.setattr("merge_carlo.simulation.engine.random_stream", stream)
    result = run_fifo(
        (pr("a"),),
        (Reviewer("r", (span(0, 10),)),),
        span=span(0, 10),
        service_seconds=1,
        loops=RevisionLoops(verification_failure_probability=probability, first_change_probability=probability),
    )
    p = result.pull_requests[0]
    assert (p.terminal_at, p.revision, p.review_visit_count) == (1, 1, 1)
    assert calls == [(0, 0), (0, 0)]


@pytest.mark.parametrize("field", ["verification_seconds", "author_response_seconds"])
@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_invalid_loop_delays(field: str, value: float) -> None:
    with pytest.raises(ValueError, match="delays"):
        if field == "verification_seconds":
            RevisionLoops(verification_seconds=value)
        else:
            RevisionLoops(author_response_seconds=value)


@pytest.mark.parametrize(
    "field", ["verification_failure_probability", "first_change_probability", "repeat_change_probability"]
)
@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan")])
def test_invalid_loop_probabilities(field: str, value: float) -> None:
    with pytest.raises(ValueError, match="probabilities"):
        if field == "verification_failure_probability":
            RevisionLoops(verification_failure_probability=value)
        elif field == "first_change_probability":
            RevisionLoops(first_change_probability=value)
        else:
            RevisionLoops(repeat_change_probability=value)


@pytest.mark.parametrize("field", ["max_review_visits", "max_verification_attempts"])
@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_invalid_loop_limits(field: str, value: float) -> None:
    from typing import cast

    with pytest.raises(ValueError, match="limits"):
        if field == "max_review_visits":
            RevisionLoops(max_review_visits=cast(int, value))
        else:
            RevisionLoops(max_verification_attempts=cast(int, value))


@pytest.mark.parametrize("seed,replication", [(-1, 0), (0, -1)])
def test_invalid_random_identity_without_proposals(seed: int, replication: int) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        run_fifo((), (), span=span(0, 1), service_seconds=1, root_seed=seed, replication=replication)


@pytest.mark.parametrize("verification,response,first_review,visits", [(10, 0, None, 0), (2, 6, 2, 1), (2, 0, 2, 2)])
def test_loop_events_at_horizon_are_censored(
    verification: float, response: float, first_review: float | None, visits: int
) -> None:
    result = run_fifo(
        (pr("a"),),
        (Reviewer("r", (span(0, 10),)),),
        span=span(0, 10),
        service_seconds=2,
        loops=RevisionLoops(
            verification_seconds=verification, author_response_seconds=response, first_change_probability=1
        ),
    )
    p = result.pull_requests[0]
    if visits == 2:
        assert p.terminal_at == 8 and not p.censored
    else:
        assert p.terminal_at == 10 and p.censored
    assert (p.first_review_at, p.review_visit_count) == (first_review, visits)
    assert not result.engine_truncated


def test_verification_is_concurrent_elapsed_time_not_runner_or_duty_service() -> None:
    result = run_fifo(
        (pr("a"), pr("b")),
        (Reviewer("r", (span(20, 50),)),),
        span=span(0, 50),
        service_seconds=3,
        loops=RevisionLoops(verification_seconds=7),
    )
    assert [(p.first_review_at, p.queue_wait_seconds, p.terminal_at) for p in result.pull_requests] == [
        (20, 13, 23),
        (23, 16, 26),
    ]
    assert result.reviewers[0].active_seconds == 6


@pytest.mark.property
@given(st.integers(0, 10000), st.sampled_from([0.0, 0.3, 1.0]), st.sampled_from([0.0, 0.6, 1.0]))
def test_loop_reproducibility_conservation_and_partial_service(seed: int, failure: float, changes: float) -> None:
    proposals = (pr("a", "r", 0.3), pr("b", "s", 1.7), pr("c", ready=2.3))
    reviewers = (Reviewer("r", (span(0, 5), span(10, 30))), Reviewer("s", (span(3, 17),)))
    loops = RevisionLoops(
        verification_seconds=0.7,
        author_response_seconds=1.3,
        verification_failure_probability=failure,
        first_change_probability=changes,
        repeat_change_probability=0.4,
        max_review_visits=3,
        max_verification_attempts=4,
    )
    result = run_fifo(proposals, reviewers, span=span(0, 30), service_seconds=3, loops=loops, root_seed=seed)
    assert result == run_fifo(
        tuple(reversed(proposals)),
        tuple(reversed(reviewers)),
        span=span(0, 30),
        service_seconds=3,
        loops=loops,
        root_seed=seed,
    )
    # Distinct exact internal times can round to the same public float.
    assert [b.at for b in result.boundaries] == sorted(b.at for b in result.boundaries)
    assert all(b.arrivals == b.merges + b.unresolved + b.work_in_progress for b in result.boundaries)
    assert sum(p.active_review_seconds for p in result.pull_requests) == pytest.approx(
        sum(r.active_seconds for r in result.reviewers)
    )
    assert all(0 <= r.active_seconds <= r.duty_seconds for r in result.reviewers)
    for p in result.pull_requests:
        assert p.review_visit_count <= 3 and p.verification_count <= 4
        assert p.queue_wait_seconds >= 0
        assert 0 <= p.active_review_seconds <= 3 * p.review_visit_count
        if p.terminal and not p.censored:
            assert p.approved_revision == p.verified_revision == p.revision


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
