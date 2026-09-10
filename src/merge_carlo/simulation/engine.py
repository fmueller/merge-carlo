"""Event-scheduled constant-service FIFO slice; times are seconds from span.start.

At equal timestamps: account preceding service, censor at the horizon, abandon
due proposals, finish reviews, admit arrivals, settle verification/author events,
then dispatch by reviewer ID. Inputs are fresh READY proposals, not saved runs.
"""

import heapq
import math
from dataclasses import dataclass, replace
from fractions import Fraction

from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import LifecycleEvent as Event
from merge_carlo.simulation.domain import PullRequest, PullRequestState
from merge_carlo.simulation.randomness import random_stream


@dataclass(frozen=True, slots=True)
class ReviewBypass:
    """Assumed eligibility and independent audit probabilities, not a classifier.

    None eligibility uses operator-supplied PullRequest.bypass_eligible labels.
    Audit flags are always resolved by the engine, once at proposal entry.
    """

    eligible_fraction: float | None
    audit_fraction: float

    def __post_init__(self) -> None:
        if self.eligible_fraction is not None and not 0 <= self.eligible_fraction <= 1:
            raise ValueError("eligible fraction must be between zero and one")
        if not 0 <= self.audit_fraction <= 1:
            raise ValueError("audit fraction must be between zero and one")


@dataclass(frozen=True, slots=True)
class Abandonment:
    """Assumed deadline probability and equally weighted elapsed-second samples.

    A singleton is a constant distribution. These are exogenous assumptions,
    not inferred from review effort; sampling occurs once per admitted proposal.
    """

    probability: float
    elapsed_seconds: tuple[float, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.probability <= 1:
            raise ValueError("abandonment probability must be between zero and one")
        if not self.elapsed_seconds or any(not math.isfinite(t) or t <= 0 for t in self.elapsed_seconds):
            raise ValueError("abandonment durations must be nonempty, finite and positive")


@dataclass(frozen=True, slots=True)
class RevisionLoops:
    """Assumed loop parameters, not measured effort or calibrated probabilities.

    Delays are constant aggregate elapsed seconds, independent of duty and
    runner capacity. Limits are inclusive per proposal across all revisions.
    Zero delays preserve the original instant-success default.
    """

    verification_seconds: float = 0
    author_response_seconds: float = 0
    verification_failure_probability: float = 0
    first_change_probability: float = 0
    repeat_change_probability: float = 0
    max_review_visits: int = 100
    max_verification_attempts: int = 100

    def __post_init__(self) -> None:
        for delay in (self.verification_seconds, self.author_response_seconds):
            if not math.isfinite(delay) or delay < 0:
                raise ValueError("loop delays must be finite and nonnegative")
        for probability in (
            self.verification_failure_probability,
            self.first_change_probability,
            self.repeat_change_probability,
        ):
            if not 0 <= probability <= 1:
                raise ValueError("loop probabilities must be between zero and one")
        for limit in (self.max_review_visits, self.max_verification_attempts):
            if type(limit) is not int or limit < 1:
                raise ValueError("loop limits must be positive integers")


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
    closed_without_merge: int = 0


@dataclass(frozen=True, slots=True)
class FIFOResult:
    pull_requests: tuple[PullRequest, ...]
    reviewers: tuple[ReviewerAccounting, ...]
    boundaries: tuple[Boundary, ...]
    limitations: tuple[str, ...]
    engine_truncated: bool = False
    modeled_review_effort_avoided_seconds: float = 0


@dataclass(frozen=True, slots=True)
class ReplicationSummary:
    """Pooled counts from nontruncated runs only; not a policy recommendation."""

    completed_replications: int
    engine_truncated_count: int
    merged: int | None
    unresolved: int | None
    closed_without_merge: int | None = None

    @property
    def comparison_incomplete(self) -> bool:
        return self.engine_truncated_count > 0 or self.completed_replications == 0

    @property
    def policy_ranking_enabled(self) -> bool:
        """Truncation gate only; downstream validity gates must also pass."""
        return not self.comparison_incomplete


def summarize_replications(results: tuple[FIFOResult, ...]) -> ReplicationSummary:
    """Exclude whole truncated replications, including any earlier merges."""
    complete = tuple(result for result in results if not result.engine_truncated)
    return ReplicationSummary(
        len(complete),
        len(results) - len(complete),
        sum(p.state is PullRequestState.MERGED for result in complete for p in result.pull_requests)
        if complete
        else None,
        sum(p.censored for result in complete for p in result.pull_requests) if complete else None,
        sum(p.state is PullRequestState.CLOSED_WITHOUT_MERGE for result in complete for p in result.pull_requests)
        if complete
        else None,
    )


def run_fifo(
    proposals: tuple[PullRequest, ...],
    reviewers: tuple[Reviewer, ...],
    *,
    span: UTCInterval,
    service_seconds: float,
    loops: RevisionLoops | None = None,
    abandonment: Abandonment | None = None,
    bypass: ReviewBypass | None = None,
    coordination_seconds: float = 0,
    root_seed: int = 0,
    replication: int = 0,
) -> FIFOResult:
    """Run over [0, span.seconds), retaining partial service at the horizon.

    Duty comes from DutyCalendar.materialize (or disjoint UTC fixtures). No
    reviewer can release an interrupted review to another reviewer. Proposals
    at/after the horizon are excluded; pre-run work and supplied deadlines are
    rejected. Abandonment samples an elapsed deadline once at entry, using
    proposal-keyed probability and duration streams independent of loop draws.
    Bypass is opt-in; eligibility and audit draws omit revision and scenario.
    Coordination is assumed elapsed delay after either approval or bypass.
    """
    loops = RevisionLoops() if loops is None else loops
    if not math.isfinite(coordination_seconds) or coordination_seconds < 0:
        raise ValueError("coordination delay must be finite and nonnegative")
    if root_seed < 0 or replication < 0:
        raise ValueError("root seed and replication must be non-negative")
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
    total_service: dict[str, Fraction] = {}
    pending: dict[Fraction, list[str]] = {}
    deadlines: dict[Fraction, list[str]] = {}
    boundaries: list[Boundary] = []
    engine_truncated = False

    def schedule(pr_id: str, at: Fraction, delay: float) -> None:
        due = at + Fraction(delay)
        if due < horizon:
            pending.setdefault(due, []).append(pr_id)
            if due != at:
                heapq.heappush(events, due)

    previous = Fraction(0)
    while events:
        now = heapq.heappop(events)
        while events and events[0] == now:
            heapq.heappop(events)
        for reviewer_id, pr_id in assigned.items():
            if any(start <= previous < end for start, end in duty[reviewer_id]):
                seconds = now - previous
                service_used[pr_id] += seconds
                total_service[pr_id] += seconds
                states[pr_id] = states[pr_id].consume_review_service(
                    float(total_service[pr_id]) - states[pr_id].active_review_seconds
                )
                active[reviewer_id] += seconds
        if now == horizon:
            for pr_id, p in states.items():
                if not p.terminal:
                    states[pr_id] = p.transition(Event.HORIZON_REACHED, at=float(now))
        else:
            for pr_id in deadlines.pop(now, []):
                p = states[pr_id]
                if not p.terminal:
                    states[pr_id] = p.transition(Event.ABANDONED, at=float(now))
            for reviewer_id, pr_id in list(assigned.items()):
                p = states[pr_id]
                if p.terminal:
                    del assigned[reviewer_id]
                    continue
                if service_used[pr_id] >= service_seconds:
                    probability = (
                        loops.first_change_probability if p.review_visit_count == 1 else loops.repeat_change_probability
                    )
                    draw = random_stream(
                        root_seed, replication, pr_id, p.review_visit_count, "requested-change"
                    ).random()
                    if draw < probability:
                        states[pr_id] = p.transition(Event.CHANGES_REQUESTED, at=float(now))
                        schedule(pr_id, now, loops.author_response_seconds)
                    else:
                        states[pr_id] = p.transition(Event.REVIEW_APPROVED, at=float(now))
                        schedule(pr_id, now, coordination_seconds)
                    del assigned[reviewer_id]
            for p in arrivals.get(now, []):
                if bypass is not None:
                    eligible = (
                        p.bypass_eligible
                        if bypass.eligible_fraction is None
                        else random_stream(root_seed, replication, p.pr_id, "bypass-eligibility").random()
                        < bypass.eligible_fraction
                    )
                    audited = eligible and (
                        random_stream(root_seed, replication, p.pr_id, "bypass-audit").random() < bypass.audit_fraction
                    )
                    p = replace(p, bypass_eligible=eligible, bypass_audited=audited)
                if (
                    abandonment is not None
                    and random_stream(root_seed, replication, p.pr_id, "abandonment-occurrence").random()
                    < abandonment.probability
                ):
                    index = int(
                        random_stream(root_seed, replication, p.pr_id, "abandonment-duration").integers(
                            len(abandonment.elapsed_seconds)
                        )
                    )
                    deadline = now + Fraction(abandonment.elapsed_seconds[index])
                    p = replace(p, abandonment_deadline=float(deadline))
                    if deadline < horizon:
                        deadlines.setdefault(deadline, []).append(p.pr_id)
                        heapq.heappush(events, deadline)
                states[p.pr_id] = p.transition(Event.START_VERIFICATION, at=float(now))
                total_service[p.pr_id] = Fraction(0)
                schedule(p.pr_id, now, loops.verification_seconds)
            while now in pending and not engine_truncated:
                for pr_id in sorted(pending.pop(now)):
                    p = states[pr_id]
                    if p.terminal:
                        continue
                    if p.state is PullRequestState.APPROVED_WAITING_MERGE:
                        states[pr_id] = p.transition(Event.MERGE_COMPLETED, at=float(now))
                    elif p.state is PullRequestState.AUTHOR_RESPONSE:
                        if p.verification_count >= loops.max_verification_attempts:
                            engine_truncated = True
                            break
                        states[pr_id] = p.transition(Event.REVISION_SUBMITTED, at=float(now))
                        schedule(pr_id, now, loops.verification_seconds)
                    else:
                        draw = random_stream(root_seed, replication, pr_id, p.revision, "verification").random()
                        if draw < loops.verification_failure_probability:
                            states[pr_id] = p.transition(Event.VERIFICATION_FAILED, at=float(now))
                            schedule(pr_id, now, loops.author_response_seconds)
                        else:
                            states[pr_id] = p.transition(Event.VERIFICATION_PASSED, at=float(now))
                            if bypass is not None and p.bypass_eligible and not p.bypass_audited:
                                states[pr_id] = states[pr_id].transition(Event.REVIEW_BYPASSED, at=float(now))
                                schedule(pr_id, now, coordination_seconds)
            queue = sorted(
                (p for p in states.values() if p.state is PullRequestState.QUEUED_FOR_REVIEW),
                key=lambda p: (p.queue_entered_at, p.pr_id, p.revision),
            )
            for r in reviewers:
                if engine_truncated:
                    break
                duty_end = next((end for start, end in duty[r.reviewer_id] if start <= now < end), None)
                if duty_end is None:
                    continue
                if r.reviewer_id not in assigned:
                    candidate = next((p for p in queue if p.author_id != r.reviewer_id), None)
                    if candidate is None:
                        continue
                    if candidate.review_visit_count >= loops.max_review_visits:
                        engine_truncated = True
                        break
                    queue.remove(candidate)
                    states[candidate.pr_id] = candidate.transition(Event.REVIEW_STARTED, at=float(now))
                    assigned[r.reviewer_id] = candidate.pr_id
                    service_used[candidate.pr_id] = Fraction(0)
                remaining = service_seconds - service_used[assigned[r.reviewer_id]]
                heapq.heappush(events, min(duty_end, now + remaining))
        merged = sum(p.state is PullRequestState.MERGED for p in states.values())
        closed = sum(p.state is PullRequestState.CLOSED_WITHOUT_MERGE for p in states.values())
        unresolved = sum(p.censored for p in states.values())
        wip = sum(not p.terminal for p in states.values())
        assert len(states) == merged + closed + unresolved + wip
        boundaries.append(Boundary(float(now), len(states), merged, wip, unresolved, closed))
        if engine_truncated:
            break
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
            if not (bypass is not None and p.bypass_eligible and not p.bypass_audited)
            and not any(
                r.reviewer_id != p.author_id and any(end > p.ready_at for _, end in duty[r.reviewer_id])
                for r in reviewers
            )
        ),
        engine_truncated,
        float(sum(p.review_bypassed for p in states.values()) * service_seconds),
    )
