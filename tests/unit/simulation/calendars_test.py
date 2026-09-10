from datetime import UTC, datetime, time, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.calendars import (
    DutyCalendar,
    LocalAbsence,
    UTCInterval,
    WeeklyWindow,
    materialize_run_bounds,
)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ("2026-03-22", [("2026-03-22T08:00", "2026-03-22T16:00"), ("2026-03-29T07:00", "2026-03-29T15:00")]),
        ("2026-10-18", [("2026-10-18T07:00", "2026-10-18T15:00"), ("2026-10-25T08:00", "2026-10-25T16:00")]),
    ],
)
def test_weekly_windows_keep_local_hours_across_dst(start: str, expected: list[tuple[str, str]]) -> None:
    bounds = materialize_run_bounds(datetime.fromisoformat(start), "Europe/Berlin", horizon_days=8)
    calendar = DutyCalendar("Europe/Berlin", (WeeklyWindow("Sunday", 6, time(9), time(17)),))

    assert calendar.materialize(bounds.observation) == tuple(UTCInterval(utc(a), utc(b)) for a, b in expected)


@pytest.mark.unit
def test_absences_split_trim_and_remove_duty_with_half_open_edges() -> None:
    calendar = DutyCalendar(
        "UTC",
        (WeeklyWindow("Monday", 0, time(9), time(17)),),
        tuple(
            LocalAbsence(datetime.fromisoformat(a), datetime.fromisoformat(b))
            for a, b in [
                ("2026-06-01T08:00", "2026-06-01T10:00"),
                ("2026-06-01T12:00", "2026-06-01T13:00"),
                ("2026-06-01T12:30", "2026-06-01T14:00"),
                ("2026-06-01T16:00", "2026-06-02T00:00"),
                ("2026-06-08T00:00", "2026-06-09T00:00"),
                ("2026-06-01T07:00", "2026-06-01T09:00"),
            ]
        ),
    )
    interval = UTCInterval(utc("2026-06-01"), utc("2026-06-09"))
    assert calendar.materialize(interval) == (
        UTCInterval(utc("2026-06-01T10:00"), utc("2026-06-01T12:00")),
        UTCInterval(utc("2026-06-01T14:00"), utc("2026-06-01T16:00")),
    )


@pytest.mark.unit
def test_empty_calendar_is_an_empty_interval_sequence() -> None:
    assert DutyCalendar("UTC", ()).materialize(UTCInterval(utc("2026-06-01"), utc("2026-06-02"))) == ()


@pytest.mark.unit
def test_overnight_carry_in_clipping_and_overlapping_windows_are_unioned() -> None:
    calendar = DutyCalendar(
        "UTC",
        (
            WeeklyWindow("late", 0, time(22), time(3)),
            WeeklyWindow("early", 1, time(2), time(5)),
            WeeklyWindow("adjacent", 1, time(5), time(6)),
        ),
    )
    assert calendar.materialize(UTCInterval(utc("2026-06-02T01:00"), utc("2026-06-02T05:30"))) == (
        UTCInterval(utc("2026-06-02T01:00"), utc("2026-06-02T05:30")),
    )


@pytest.mark.unit
@pytest.mark.parametrize(("day", "error"), [("2026-03-29", "nonexistent"), ("2026-10-25", "ambiguous")])
def test_rejects_dst_boundaries_in_windows_absences_and_run_bounds(day: str, error: str) -> None:
    local = datetime.fromisoformat(f"{day}T02:30")
    with pytest.raises(ValueError, match=error):
        materialize_run_bounds(local, "Europe/Berlin", horizon_days=1)
    for window in (WeeklyWindow("start", 6, time(2, 30), time(4)), WeeklyWindow("end", 6, time(1), time(2, 30))):
        with pytest.raises(ValueError, match=error):
            DutyCalendar("Europe/Berlin", (window,)).materialize(UTCInterval(utc(day), utc(day) + timedelta(days=1)))
    with pytest.raises(ValueError, match=error):
        DutyCalendar("Europe/Berlin", (), (LocalAbsence(local, local + timedelta(hours=2)),))
    with pytest.raises(ValueError, match=error):
        DutyCalendar("Europe/Berlin", (), (LocalAbsence(local - timedelta(hours=2), local),))


@pytest.mark.unit
@pytest.mark.parametrize(("start", "end"), [(time(1), time(2)), (time(2), time(2, 30))])
def test_subday_fall_back_span_rejects_possibly_overlapping_ambiguous_windows(start: time, end: time) -> None:
    calendar = DutyCalendar("Europe/Berlin", (WeeklyWindow("fold", 6, start, end),))
    span = UTCInterval(utc("2026-10-25T00:45"), utc("2026-10-25T01:15"))
    with pytest.raises(ValueError, match="ambiguous local boundary .* in Europe/Berlin"):
        calendar.materialize(span)


@pytest.mark.unit
def test_ambiguous_windows_wholly_outside_the_utc_span_do_not_fail() -> None:
    calendar = DutyCalendar("Europe/Berlin", (WeeklyWindow("fold", 6, time(2), time(2, 30)),))
    for span in (
        UTCInterval(utc("2026-10-24T21:00"), utc("2026-10-25T00:00")),
        UTCInterval(utc("2026-10-25T01:30"), utc("2026-10-25T04:00")),
    ):
        assert calendar.materialize(span) == ()


@pytest.mark.unit
@pytest.mark.parametrize(("start", "seconds"), [("2026-03-28T12:00", 169200), ("2026-10-24T12:00", 176400)])
def test_horizon_and_warmup_are_local_increments_with_exact_utc_elapsed(start: str, seconds: int) -> None:
    local = datetime.fromisoformat(start)
    bounds = materialize_run_bounds(local, "Europe/Berlin", horizon_days=2, warmup_days=2)
    assert bounds.observation.seconds == seconds
    assert bounds.warmup_seconds == 172800
    assert bounds.warmup_start == bounds.observation.start - timedelta(days=2)
    assert bounds.observation.start == local.replace(tzinfo=UTC) - timedelta(hours=1 if local.month == 3 else 2)
    assert bounds.observation.end == (local + timedelta(days=2)).replace(tzinfo=UTC) - timedelta(
        hours=2 if local.month == 3 else 1
    )
    after = materialize_run_bounds(local + timedelta(days=2), "Europe/Berlin", horizon_days=1, warmup_days=2)
    assert after.warmup_seconds == seconds
    assert after.warmup_start == bounds.observation.start
    no_warmup = materialize_run_bounds(local, "Europe/Berlin", horizon_days=1)
    assert no_warmup.warmup_seconds == 0
    assert no_warmup.warmup_start == no_warmup.observation.start


@pytest.mark.unit
def test_run_increment_endpoints_are_validated() -> None:
    with pytest.raises(ValueError, match="nonexistent"):
        materialize_run_bounds(datetime(2026, 3, 28, 2, 30), "Europe/Berlin", horizon_days=1)
    with pytest.raises(ValueError, match="ambiguous"):
        materialize_run_bounds(datetime(2026, 10, 26, 2, 30), "Europe/Berlin", horizon_days=1, warmup_days=1)


@pytest.mark.unit
def test_invalid_contracts_fail_clearly() -> None:
    for weekday in (-1, 7):
        with pytest.raises(ValueError, match="weekday"):
            WeeklyWindow("bad", weekday, time(9), time(17))
    with pytest.raises(ValueError, match="name"):
        WeeklyWindow("", 0, time(9), time(17))
    with pytest.raises(ValueError, match="distinct"):
        WeeklyWindow("empty", 0, time(9), time(9))
    with pytest.raises(ValueError, match="naive"):
        WeeklyWindow("aware", 0, time(9, tzinfo=UTC), time(17))
    with pytest.raises(ValueError, match="timezone"):
        DutyCalendar("Not/AZone", ())
    with pytest.raises(ValueError, match="unique"):
        DutyCalendar("UTC", (WeeklyWindow("same", 0, time(9), time(17)),) * 2)
    with pytest.raises(ValueError, match="after"):
        LocalAbsence(datetime(2026, 1, 2), datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="naive"):
        LocalAbsence(utc("2026-01-01"), utc("2026-01-02"))
    with pytest.raises(ValueError, match="UTC"):
        UTCInterval(datetime(2026, 1, 1), datetime(2026, 1, 2))
    with pytest.raises(ValueError, match="after"):
        UTCInterval(utc("2026-01-01"), utc("2026-01-01"))
    for horizon, warmup in ((0, 0), (-1, 0), (1, -1)):
        with pytest.raises(ValueError, match="days"):
            materialize_run_bounds(datetime(2026, 1, 1), "UTC", horizon_days=horizon, warmup_days=warmup)
    with pytest.raises(ValueError, match="naive"):
        materialize_run_bounds(utc("2026-01-01"), "UTC", horizon_days=1)


@pytest.mark.property
@given(start_hour=st.integers(0, 22), length=st.integers(1, 12))
def test_absence_subtraction_conserves_available_seconds(start_hour: int, length: int) -> None:
    day = datetime(2026, 6, 1)
    absence_start = day + timedelta(hours=start_hour)
    absence_end = absence_start + timedelta(hours=length)
    calendar = DutyCalendar(
        "UTC", (WeeklyWindow("work", 0, time(9), time(17)),), (LocalAbsence(absence_start, absence_end),)
    )
    span = UTCInterval(utc("2026-06-01"), utc("2026-06-02"))
    intervals = calendar.materialize(span)
    removed_hours = max(0, min(17, start_hour + length) - max(9, start_hour))
    assert sum(interval.seconds for interval in intervals) == (8 - removed_hours) * 3600
    assert all(a.end < b.start for a, b in zip(intervals, intervals[1:], strict=False))
    assert intervals == calendar.materialize(span)
