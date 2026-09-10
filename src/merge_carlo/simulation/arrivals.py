"""Resample complete local weeks without separating arrival attribute bundles."""

import math
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from merge_carlo.simulation.calendars import UTCInterval, _local_to_utc, _zone
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.randomness import random_stream


@dataclass(frozen=True, slots=True)
class AdditiveAI:
    """Assumed additional demand as a fraction of each full baseline week."""

    fraction: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.fraction) or self.fraction < 0:
            raise ValueError("additive fraction must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class ReplacementAI:
    """Assumed probability of reassigning each known-human proposal to AI."""

    fraction: float

    def __post_init__(self) -> None:
        if not 0 <= self.fraction <= 1:
            raise ValueError("replacement fraction must be between zero and one")


@dataclass(frozen=True, slots=True)
class TemplateArrival:
    """Wall-clock offset from Monday midnight and its observed attribute bundle."""

    offset: timedelta
    author_id: str
    origin: WorkOrigin

    def __post_init__(self) -> None:
        if not timedelta() <= self.offset < timedelta(days=7):
            raise ValueError("arrival offset must be within one local week")
        if not self.author_id:
            raise ValueError("author identifier must not be empty")


@dataclass(frozen=True, slots=True)
class WeekTemplate:
    """Caller-certified complete training week; empty weeks must be retained.

    The extractor owns cutoff/coverage validation. Arrival tuple positions are
    stable source identities, including for simultaneous arrivals.
    """

    week_start: date
    arrivals: tuple[TemplateArrival, ...]

    def __post_init__(self) -> None:
        if self.week_start.weekday() != 0:
            raise ValueError("training week must start on Monday")


@dataclass(frozen=True, slots=True)
class ProposalSchedule:
    proposals: tuple[PullRequest, ...]
    limitations: tuple[str, ...]

    @property
    def cohort_mix(self) -> dict[WorkOrigin, int]:
        """Realized counts after clipping, including zero-count service cohorts.

        Origin selects the service cohort; no individual effort is inferred.
        """
        return {origin: sum(p.origin is origin for p in self.proposals) for origin in WorkOrigin}


def generate_proposals(
    templates: tuple[WeekTemplate, ...],
    *,
    span: UTCInterval,
    timezone: str,
    root_seed: int,
    replication: int,
    scenario: AdditiveAI | ReplacementAI | None = None,
) -> ProposalSchedule:
    """Sample each intersecting local week, then clip to the half-open UTC span.

    Readiness is elapsed seconds from span.start, suitable for run_fifo. Week
    selection uses calendar-date keys, independent of scenario/call order and
    horizon length. IDs identify target week and source tuple position; use
    them with random_stream for subsequent shared latent draws. DST gaps and
    folds in sampled weeks are rejected by the calendar's strict mapping.

    Additions use floor(fraction * full_week_count + U), with one keyed U
    per week. A separately keyed stream samples bundled offsets/authors from
    the pooled training arrivals. Added IDs use draw position, so larger loads
    extend the same prefix. Transform before clipping, never rescale a partial
    week. Replacement keeps IDs (and therefore downstream latent draw keys).
    """
    if not templates:
        raise ValueError("at least one complete training week is required")
    if len({template.week_start for template in templates}) != len(templates):
        raise ValueError("training weeks must be unique")
    ordered = sorted(templates, key=lambda template: template.week_start)
    pool = tuple(arrival for template in ordered for arrival in template.arrivals)
    zone = _zone(timezone)
    local_start = span.start.astimezone(zone).date()
    monday = local_start - timedelta(days=local_start.weekday())
    local_end = span.end.astimezone(zone).replace(tzinfo=None)
    proposals: list[PullRequest] = []
    while datetime.combine(monday, time()) < local_end:
        key = monday.isoformat()
        stream = random_stream(root_seed, replication, "arrival-week", key)
        template = ordered[int(stream.integers(len(ordered)))]
        arrivals = [(f"baseline:{key}:{index}", arrival) for index, arrival in enumerate(template.arrivals)]
        if isinstance(scenario, AdditiveAI):
            uniform = random_stream(root_seed, replication, "ai-additive-count", key).random()
            count = math.floor(scenario.fraction * len(template.arrivals) + uniform)
            added_stream = random_stream(root_seed, replication, "ai-additive-template", key)
            for index in range(count):
                arrival = pool[int(added_stream.integers(len(pool)))]
                arrivals.append((f"ai-additive:{key}:{index}", replace(arrival, origin=WorkOrigin.AI)))
        for pr_id, arrival in arrivals:
            if (
                isinstance(scenario, ReplacementAI)
                and arrival.origin is WorkOrigin.HUMAN
                and random_stream(root_seed, replication, pr_id, "ai-replacement").random() < scenario.fraction
            ):
                arrival = replace(arrival, origin=WorkOrigin.AI)
            ready = _local_to_utc(datetime.combine(monday, time()) + arrival.offset, zone)
            if span.start <= ready < span.end:
                proposals.append(
                    PullRequest(
                        pr_id,
                        arrival.author_id,
                        arrival.origin,
                        (ready - span.start).total_seconds(),
                    )
                )
        monday += timedelta(days=7)
    return ProposalSchedule(
        tuple(sorted(proposals, key=lambda proposal: (proposal.ready_at, proposal.pr_id))),
        ("exploratory_only",) if len(ordered) < 8 else (),
    )
