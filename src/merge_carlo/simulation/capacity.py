"""Resolve declared capacity changes without touching proposals or random streams."""

from collections.abc import Mapping
from dataclasses import replace

from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, UTCInterval
from merge_carlo.simulation.engine import Reviewer


def materialize_reviewers(
    calendars: Mapping[str, DutyCalendar],
    reviewer_calendars: Mapping[str, str],
    *,
    span: UTCInterval,
    overrides: Mapping[str, DutyCalendar] | None = None,
    absences: Mapping[str, tuple[LocalAbsence, ...]] | None = None,
) -> tuple[Reviewer, ...]:
    """Replace named calendars completely, then append reviewer-specific absences.

    Naive absence boundaries use the resolved calendar's timezone. Empty duty
    retains reviewer identity without creating a zero-capacity resource. Inputs
    remain unchanged; unknown calendar or reviewer references are errors.
    """
    overrides = {} if overrides is None else overrides
    absences = {} if absences is None else absences
    if overrides.keys() - calendars.keys():
        raise ValueError("unknown calendar override")
    if absences.keys() - reviewer_calendars.keys():
        raise ValueError("unknown reviewer absence")
    if set(reviewer_calendars.values()) - calendars.keys():
        raise ValueError("unknown reviewer calendar")
    resolved = dict(calendars)
    resolved.update(overrides)
    reviewers = []
    for reviewer_id, calendar_name in sorted(reviewer_calendars.items()):
        calendar = resolved[calendar_name]
        calendar = replace(calendar, absences=calendar.absences + absences.get(reviewer_id, ()))
        reviewers.append(Reviewer(reviewer_id, calendar.materialize(span)))
    return tuple(reviewers)
