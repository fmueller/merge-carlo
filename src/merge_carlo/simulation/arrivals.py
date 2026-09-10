"""Resample complete local weeks without separating arrival attribute bundles."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from merge_carlo.simulation.calendars import UTCInterval, _local_to_utc, _zone
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.randomness import random_stream


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


def generate_proposals(
    templates: tuple[WeekTemplate, ...],
    *,
    span: UTCInterval,
    timezone: str,
    root_seed: int,
    replication: int,
) -> ProposalSchedule:
    """Sample each intersecting local week, then clip to the half-open UTC span.

    Readiness is elapsed seconds from span.start, suitable for run_fifo. Week
    selection uses calendar-date keys, independent of scenario/call order and
    horizon length. IDs identify target week and source tuple position; use
    them with random_stream for subsequent shared latent draws. DST gaps and
    folds in sampled weeks are rejected by the calendar's strict mapping.
    """
    if not templates:
        raise ValueError("at least one complete training week is required")
    if len({template.week_start for template in templates}) != len(templates):
        raise ValueError("training weeks must be unique")
    ordered = sorted(templates, key=lambda template: template.week_start)
    zone = _zone(timezone)
    local_start = span.start.astimezone(zone).date()
    monday = local_start - timedelta(days=local_start.weekday())
    local_end = span.end.astimezone(zone).replace(tzinfo=None)
    proposals: list[PullRequest] = []
    while datetime.combine(monday, time()) < local_end:
        key = monday.isoformat()
        stream = random_stream(root_seed, replication, "arrival-week", key)
        template = ordered[int(stream.integers(len(ordered)))]
        for index, arrival in enumerate(template.arrivals):
            ready = _local_to_utc(datetime.combine(monday, time()) + arrival.offset, zone)
            if span.start <= ready < span.end:
                proposals.append(
                    PullRequest(
                        f"baseline:{key}:{index}",
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
