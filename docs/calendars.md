# Calendar semantics

`merge_carlo.simulation.calendars` provides offline simulation primitives, not
a CLI command or a YAML configuration loader. The scheduler and versioned
configuration/result artifacts remain separate tracked work.

- A `DutyCalendar` describes one reviewer's declared availability in an IANA
  timezone understood by Python `zoneinfo` and the installed timezone database.
- A `WeeklyWindow` has a unique name within the calendar, a weekday (Monday is
  0, Sunday is 6), and naive local start/end times. An end earlier than the
  start belongs to the following local date. Equal endpoints are rejected;
  represent continuous availability with adjoining windows instead.
- `LocalAbsence` holds naive, dated local start/end datetimes in the calendar's
  timezone. A full-day absence ends at midnight of the following day.
- All intervals are half-open: start is included, end is excluded. Materialized
  intervals are UTC, sorted, clipped to the requested span, and disjoint.
  Overlapping or adjacent duty windows are unioned before absences are
  subtracted, so availability cannot be counted twice. Partial absences split
  windows. Empty calendars or fully absent reviewers yield an empty tuple;
  no zero-capacity resource is created.
- Ambiguous fall-back and nonexistent spring-forward local boundaries raise
  `ValueError` naming the boundary and timezone. An explicit `fold` does not
  override this rejection policy. Dated absences are checked when constructing
  the calendar; recurring windows are checked for dates overlapping the span
  during materialization. Materialize all calendars before starting a run.
  Valid boundaries on either side of a DST transition are allowed: elapsed
  duty seconds then differ from the wall-clock duration.
- `materialize_run_bounds` takes a naive local observation start, a timezone,
  positive integer `horizon_days`, and nonnegative integer `warmup_days`.
  The observation end is that many local days after the start; the warm-up
  begins that many local days before it. All three boundaries follow the same
  DST rejection policy. `observation.start`, `observation.end`, and
  `warmup_start` record UTC instants; `observation.seconds` and
  `warmup_seconds` expose exact elapsed seconds. Zero warm-up is supported.
  Use `UTCInterval(bounds.warmup_start, bounds.observation.end)` to materialize
  duty for the entire run, including warm-up.

For example, this synthetic Sunday calendar crosses Berlin's spring change:

```python
from datetime import datetime, time

from merge_carlo.simulation.calendars import (
    DutyCalendar,
    WeeklyWindow,
    materialize_run_bounds,
)

bounds = materialize_run_bounds(
    datetime(2026, 3, 22), "Europe/Berlin", horizon_days=8,
)
calendar = DutyCalendar(
    "Europe/Berlin", (WeeklyWindow("Sunday", 6, time(9), time(17)),),
)
intervals = calendar.materialize(bounds.observation)
assert [interval.start.hour for interval in intervals] == [8, 7]
assert bounds.observation.seconds == 687600  # eight local days minus one hour
```

These are declared duty seconds, not inferred service effort. No holidays are
added automatically. This primitive does not schedule reviews or persist a
result artifact.
