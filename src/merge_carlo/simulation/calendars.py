"""Materialize local weekly duty and absences into half-open UTC intervals.

Ambiguous and nonexistent local boundaries are rejected, never guessed. Call
materialize before starting a simulation so boundary errors fail before a run.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from datetime import timezone as FixedOffset
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown timezone: {name}") from exc


def _local_to_utc(local: datetime, zone: ZoneInfo) -> datetime:
    if local.tzinfo is not None:
        raise ValueError("local boundaries must be naive; supply the calendar timezone separately")
    candidates = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None) == local:
            candidates.add(candidate)
    if not candidates:
        raise ValueError(f"nonexistent local boundary {local.isoformat()} in {zone.key}")
    if len(candidates) > 1:
        raise ValueError(f"ambiguous local boundary {local.isoformat()} in {zone.key}")
    return candidates.pop()


@dataclass(frozen=True, slots=True)
class UTCInterval:
    """A nonempty half-open UTC interval; seconds are elapsed, not wall time."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if any(value.utcoffset() != timedelta(0) for value in (self.start, self.end)):
            raise ValueError("interval boundaries must be UTC")
        # Normalize even zero-offset ZoneInfo values before datetime arithmetic.
        object.__setattr__(self, "start", self.start.astimezone(UTC))
        object.__setattr__(self, "end", self.end.astimezone(UTC))
        if self.end <= self.start:
            raise ValueError("interval end must be after start")

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True, slots=True)
class WeeklyWindow:
    """Named window, Monday=0; an earlier end means the following local day."""

    name: str
    weekday: int
    start: time
    end: time

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("window name must not be empty")
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be between 0 (Monday) and 6 (Sunday)")
        if self.start.tzinfo is not None or self.end.tzinfo is not None:
            raise ValueError("weekly window times must be naive")
        if self.start == self.end:
            raise ValueError("weekly window boundaries must be distinct")


@dataclass(frozen=True, slots=True)
class LocalAbsence:
    """Half-open absence: naive boundaries use the calendar zone, aware ones their offset."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        for boundary in (self.start, self.end):
            if boundary.tzinfo is not None and not isinstance(boundary.tzinfo, FixedOffset):
                raise ValueError("absence boundaries must be naive or carry an explicit fixed offset")
        if self.start.tzinfo is None and self.end.tzinfo is None and self.end <= self.start:
            raise ValueError("absence end must be after start")

    def materialize(self, timezone: str) -> UTCInterval:
        """Resolve each boundary, then validate elapsed ordering in UTC."""
        zone = _zone(timezone)
        start = self.start.astimezone(UTC) if self.start.tzinfo is not None else _local_to_utc(self.start, zone)
        end = self.end.astimezone(UTC) if self.end.tzinfo is not None else _local_to_utc(self.end, zone)
        return UTCInterval(start, end)


@dataclass(frozen=True, slots=True)
class RunBounds:
    """Observation bounds and the preceding warm-up's UTC start."""

    observation: UTCInterval
    warmup_start: datetime

    @property
    def warmup_seconds(self) -> float:
        return (self.observation.start - self.warmup_start).total_seconds()


def materialize_run_bounds(
    observation_start: datetime,
    timezone: str,
    *,
    horizon_days: int,
    warmup_days: int = 0,
) -> RunBounds:
    """Add horizon days and subtract warm-up days in local calendar time."""

    if horizon_days <= 0 or warmup_days < 0:
        raise ValueError("horizon days must be positive and warmup days nonnegative")
    zone = _zone(timezone)
    start = _local_to_utc(observation_start, zone)
    end = _local_to_utc(observation_start + timedelta(days=horizon_days), zone)
    warmup_start = _local_to_utc(observation_start - timedelta(days=warmup_days), zone)
    return RunBounds(UTCInterval(start, end), warmup_start)


@dataclass(frozen=True, slots=True)
class DutyCalendar:
    """One reviewer's availability; no windows means no duty, not capacity zero."""

    timezone: str
    windows: tuple[WeeklyWindow, ...]
    absences: tuple[LocalAbsence, ...] = ()

    def __post_init__(self) -> None:
        _zone(self.timezone)
        if len({window.name for window in self.windows}) != len(self.windows):
            raise ValueError("weekly window names must be unique within a calendar")
        for absence in self.absences:
            absence.materialize(self.timezone)

    def materialize(self, span: UTCInterval) -> tuple[UTCInterval, ...]:
        """Return sorted, disjoint duty clipped to span after subtracting absences.

        Overlapping or touching windows are unioned to avoid double-counting
        duty. Include the preceding local date for overnight carry-in shifts.
        """

        zone = _zone(self.timezone)
        local_span_start = span.start.astimezone(zone).replace(tzinfo=None)
        local_span_end = span.end.astimezone(zone).replace(tzinfo=None)
        day = local_span_start.date() - timedelta(days=1)
        last_day = local_span_end.date()
        intervals: list[UTCInterval] = []
        while day <= last_day:
            for window in self.windows:
                if day.weekday() != window.weekday:
                    continue
                local_start = datetime.combine(day, window.start)
                end_day = day + timedelta(days=1) if window.end < window.start else day
                local_end = datetime.combine(end_day, window.end)
                # Check possible overlap in UTC: wall time can move backwards
                # within span. Both folds bound all possible interpretations;
                # overlapping boundaries still undergo strict validation below.
                earliest_start = min(local_start.replace(tzinfo=zone, fold=fold).astimezone(UTC) for fold in (0, 1))
                latest_end = max(local_end.replace(tzinfo=zone, fold=fold).astimezone(UTC) for fold in (0, 1))
                if latest_end <= span.start or earliest_start >= span.end:
                    continue
                start = max(span.start, _local_to_utc(local_start, zone))
                end = min(span.end, _local_to_utc(local_end, zone))
                if start < end:
                    intervals.append(UTCInterval(start, end))
            day += timedelta(days=1)

        merged: list[UTCInterval] = []
        for interval in sorted(intervals, key=lambda interval: interval.start):
            if merged and interval.start <= merged[-1].end:
                merged[-1] = UTCInterval(merged[-1].start, max(merged[-1].end, interval.end))
            else:
                merged.append(interval)
        for absence in self.absences:
            absent = absence.materialize(self.timezone)
            absent_start, absent_end = absent.start, absent.end
            remaining: list[UTCInterval] = []
            for interval in merged:
                if absent_end <= interval.start or absent_start >= interval.end:
                    remaining.append(interval)
                    continue
                if interval.start < absent_start:
                    remaining.append(UTCInterval(interval.start, absent_start))
                if absent_end < interval.end:
                    remaining.append(UTCInterval(absent_end, interval.end))
            merged = remaining
        return tuple(merged)
