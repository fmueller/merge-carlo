from datetime import UTC, datetime, time

import pytest

from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, UTCInterval, WeeklyWindow
from merge_carlo.simulation.capacity import materialize_reviewers
from merge_carlo.simulation.domain import PullRequest, WorkOrigin
from merge_carlo.simulation.engine import RevisionLoops, run_fifo

pytestmark = pytest.mark.unit
SPAN = UTCInterval(datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC))
BASE = DutyCalendar("UTC", (WeeklyWindow("work", 0, time(9), time(10)),))


def test_override_replaces_entire_calendar_without_mutating_inputs() -> None:
    old = DutyCalendar("UTC", BASE.windows, (LocalAbsence(datetime(2026, 6, 1), datetime(2026, 6, 2)),))
    replacement = DutyCalendar("Europe/Berlin", (WeeklyWindow("new", 0, time(14), time(15)),))
    calendars = {"team": old, "other": BASE}
    reviewers = materialize_reviewers(
        calendars,
        {"b": "team", "a": "team", "c": "other"},
        span=SPAN,
        overrides={"team": replacement},
        absences={"a": (LocalAbsence(datetime(2026, 6, 1, 14, 15), datetime(2026, 6, 1, 14, 45)),)},
    )
    assert [r.reviewer_id for r in reviewers] == ["a", "b", "c"]
    assert [[(i.start.hour, i.start.minute, i.end.hour, i.end.minute) for i in r.duty] for r in reviewers] == [
        [(12, 0, 12, 15), (12, 45, 13, 0)],
        [(12, 0, 13, 0)],
        [(9, 0, 10, 0)],
    ]
    assert calendars == {"team": old, "other": BASE}
    assert old.absences and replacement.absences == ()


@pytest.mark.parametrize("kind", ["override", "absence", "binding"])
def test_unknown_names_are_rejected(kind: str) -> None:
    with pytest.raises(ValueError, match="unknown"):
        materialize_reviewers(
            {"team": BASE},
            {"r": "missing" if kind == "binding" else "team"},
            span=SPAN,
            overrides={"missing": BASE} if kind == "override" else {},
            absences={"missing": ()} if kind == "absence" else {},
        )


def test_capacity_only_changes_duty_and_noop_preserves_keyed_run() -> None:
    proposals = tuple(PullRequest(str(i), "author", WorkOrigin.HUMAN, 9 * 3600) for i in range(3))
    baseline = materialize_reviewers({"team": BASE}, {"r": "team"}, span=SPAN)
    noop = materialize_reviewers({"team": BASE}, {"r": "team"}, span=SPAN, overrides={"team": BASE})
    loops = RevisionLoops(first_change_probability=0.4, repeat_change_probability=0.2)
    assert run_fifo(proposals, baseline, span=SPAN, service_seconds=600, loops=loops, root_seed=83) == run_fifo(
        proposals,
        noop,
        span=SPAN,
        service_seconds=600,
        loops=loops,
        root_seed=83,
    )
    removed = materialize_reviewers(
        {"team": BASE}, {"r": "team"}, span=SPAN, overrides={"team": DutyCalendar("UTC", ())}
    )
    absent = materialize_reviewers(
        {"team": BASE}, {"r": "team"}, span=SPAN, absences={"r": (LocalAbsence(SPAN.start, SPAN.end),)}
    )
    assert absent == removed
    empty = run_fifo(proposals, removed, span=SPAN, service_seconds=600)
    assert all(p.censored for p in empty.pull_requests)
    assert empty.reviewers[0].duty_seconds == 0
    added = materialize_reviewers({"team": BASE}, {"r": "team", "s": "team"}, span=SPAN)
    one = run_fifo(proposals, baseline, span=SPAN, service_seconds=600)
    two = run_fifo(proposals, added, span=SPAN, service_seconds=600)
    assert [p.terminal_at for p in one.pull_requests] == [33000, 33600, 34200]
    assert [p.terminal_at for p in two.pull_requests] == [33000, 33000, 33600]
    assert all(p.ready_at == 32400 and p.revision == 1 for p in two.pull_requests)
