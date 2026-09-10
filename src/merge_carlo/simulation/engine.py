"""Event-scheduled constant-service FIFO slice; times are seconds from span.start.

At equal timestamps: account preceding service, censor at the horizon, finish
reviews, admit arrivals, then dispatch by reviewer ID. Verification and merge
are instantaneous successes. Inputs are fresh READY proposals, not saved runs.
"""

import heapq
import math
from dataclasses import dataclass
from fractions import Fraction

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import LifecycleEvent as Event
from merge_carlo.simulation.domain import PullRequest, PullRequestState


@dataclass(frozen=True, slots=True)
class Reviewer:
    reviewer_id: str
    duty: tuple[UTCInterval, ...]

    def __post_init__(self) -> None:
        if not self.reviewer_id:
            raise ValueError("reviewer identifier must not be empty")
        if any(a.end > b.start for a, b in zip(self.duty, self.duty[1:], strict=False)):
            raise ValueError("duty intervals must be sorted and disjoint")


@dataclass(frozen=True, slots=True)
class ReviewerAccounting:
    reviewer_id: str
    active_seconds: float
    duty_seconds: float


@dataclass(frozen=True, slots=True)
class Boundary:
    at: float
    arrivals: int
    merges: int
    work_in_progress: int
    unresolved: int


@dataclass(frozen=True, slots=True)
class FIFOResult:
    pull_requests: tuple[PullRequest, ...]
    reviewers: tuple[ReviewerAccounting, ...]
    boundaries: tuple[Boundary, ...]
    limitations: tuple[str, ...]


def run_fifo(
    proposals: tuple[PullRequest, ...],
    reviewers: tuple[Reviewer, ...],
    *,
    span: UTCInterval,
    service_seconds: float,
) -> FIFOResult:
    """Run over [0, span.seconds), retaining partial service at the horizon.

    Duty comes from DutyCalendar.materialize (or disjoint UTC fixtures). No
    reviewer can release an interrupted review to another reviewer. Proposals
    at/after the horizon are excluded; pre-run work and deadlines are rejected.
    """
    if not math.isfinite(service_seconds) or service_seconds < 1:
        raise ValueError("constant service must be finite and at least one second")
    service_seconds = math.ceil(service_seconds)
    if len({p.pr_id for p in proposals}) != len(proposals):
        raise ValueError("pull request identifiers must be unique")
    if len({r.reviewer_id for r in reviewers}) != len(reviewers):
        raise ValueError("reviewer identifiers must be unique")
    for p in proposals:
        fresh = PullRequest(
            p.pr_id,
            p.author_id,
            p.origin,
            p.ready_at,
            revision=p.revision,
            bypass_eligible=p.bypass_eligible,
            bypass_audited=p.bypass_audited,
        )
        if p != fresh or p.ready_at < 0:
            raise ValueError("engine requires fresh READY proposals without abandonment deadlines")

    # Exact internal arithmetic prevents a fractional completion from rounding
    # back to the same event time with a tiny positive amount of service left.
    horizon = Fraction(span.seconds)
    reviewers = tuple(sorted(reviewers, key=lambda r: r.reviewer_id))
    duty = {
        r.reviewer_id: tuple(
            (
                max(Fraction(0), Fraction((i.start - span.start).total_seconds())),
                min(horizon, Fraction((i.end - span.start).total_seconds())),
            )
            for i in r.duty
            if i.start < span.end and i.end > span.start
        )
        for r in reviewers
    }
    arrivals: dict[Fraction, list[PullRequest]] = {}
    for p in sorted(proposals, key=lambda p: p.pr_id):
        if p.ready_at < horizon:
            arrivals.setdefault(Fraction(p.ready_at), []).append(p)
    times = {Fraction(0), horizon, *arrivals}
    for intervals in duty.values():
        for start, end in intervals:
            times.update((start, end))
    events = list(times)
    heapq.heapify(events)
    states: dict[str, PullRequest] = {}
    assigned: dict[str, str] = {}
    active = dict.fromkeys(duty, Fraction(0))
    service_used: dict[str, Fraction] = {}
    boundaries: list[Boundary] = []
    previous = Fraction(0)
    while events:
        now = heapq.heappop(events)
        while events and events[0] == now:
            heapq.heappop(events)
        for reviewer_id, pr_id in assigned.items():
            if any(start <= previous < end for start, end in duty[reviewer_id]):
                seconds = now - previous
                service_used[pr_id] += seconds
                states[pr_id] = states[pr_id].consume_review_service(
                    float(service_used[pr_id]) - states[pr_id].active_review_seconds
                )
                active[reviewer_id] += seconds
        if now == horizon:
            for pr_id, p in states.items():
                if not p.terminal:
                    states[pr_id] = p.transition(Event.HORIZON_REACHED, at=float(now))
        else:
            for reviewer_id, pr_id in list(assigned.items()):
                p = states[pr_id]
                if service_used[pr_id] >= service_seconds:
                    states[pr_id] = p.transition(Event.REVIEW_APPROVED, at=float(now)).transition(
                        Event.MERGE_COMPLETED, at=float(now)
                    )
                    del assigned[reviewer_id]
            for p in arrivals.get(now, []):
                states[p.pr_id] = p.transition(Event.START_VERIFICATION, at=float(now)).transition(
                    Event.VERIFICATION_PASSED, at=float(now)
                )
            queue = sorted(
                (p for p in states.values() if p.state is PullRequestState.QUEUED_FOR_REVIEW),
                key=lambda p: (p.queue_entered_at, p.pr_id, p.revision),
            )
            for r in reviewers:
                duty_end = next((end for start, end in duty[r.reviewer_id] if start <= now < end), None)
                if duty_end is None:
                    continue
                if r.reviewer_id not in assigned:
                    candidate = next((p for p in queue if p.author_id != r.reviewer_id), None)
                    if candidate is None:
                        continue
                    queue.remove(candidate)
                    states[candidate.pr_id] = candidate.transition(Event.REVIEW_STARTED, at=float(now))
                    assigned[r.reviewer_id] = candidate.pr_id
                    service_used[candidate.pr_id] = Fraction(0)
                remaining = service_seconds - service_used[assigned[r.reviewer_id]]
                heapq.heappush(events, min(duty_end, now + remaining))
        merged = sum(p.state is PullRequestState.MERGED for p in states.values())
        unresolved = sum(p.censored for p in states.values())
        wip = sum(not p.terminal for p in states.values())
        assert len(states) == merged + unresolved + wip
        boundaries.append(Boundary(float(now), len(states), merged, wip, unresolved))
        previous = now
    return FIFOResult(
        tuple(states[key] for key in sorted(states)),
        tuple(
            ReviewerAccounting(
                r.reviewer_id,
                float(active[r.reviewer_id]),
                float(sum(end - start for start, end in duty[r.reviewer_id])),
            )
            for r in reviewers
        ),
        tuple(boundaries),
        tuple(
            f"no_eligible_reviewer:{p.pr_id}"
            for p in sorted(states.values(), key=lambda p: p.pr_id)
            if not any(
                r.reviewer_id != p.author_id and any(end > p.ready_at for _, end in duty[r.reviewer_id])
                for r in reviewers
            )
        ),
    )
