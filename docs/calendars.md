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
- `LocalAbsence` holds dated start/end datetimes. Naive boundaries use the
  calendar's timezone; an explicit offset determines that boundary's UTC
  instant instead. Boundaries may mix these forms; ordering is checked after
  UTC conversion. A full-day absence ends at midnight of the following day.
  Offsets must use `datetime.timezone` (as ISO offset parsing produces).
  Named-zone and custom `tzinfo` boundaries are rejected; use naive local
  datetimes or supply an explicit fixed offset instead.
- All intervals are half-open: start is included, end is excluded. Materialized
  intervals are UTC, sorted, clipped to the requested span, and disjoint.
  Overlapping or adjacent duty windows are unioned before absences are
  subtracted, so availability cannot be counted twice. Partial absences split
  windows. Empty calendars or fully absent reviewers yield an empty tuple;
  no zero-capacity resource is created.
- Ambiguous fall-back and nonexistent spring-forward local boundaries raise
  `ValueError` naming the boundary and timezone. A naive `fold` does not
  override this rejection policy; offset-aware absences specify an instant.
  Dated absences are checked when constructing
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

## Capacity scenarios

`simulation.capacity.materialize_reviewers(calendars, reviewer_calendars,
span=..., overrides=..., absences=...)` returns reviewers ready for `run_fifo`.
`calendars` maps calendar names to `DutyCalendar` values; `reviewer_calendars`
maps reviewer IDs to calendar names. Optional `overrides` replaces each named
calendar completely, including timezone, windows and calendar-level absences.
Optional `absences` maps reviewer IDs to additional absence tuples, applied
after replacement in the resolved calendar's timezone. Shared calendars do
not cause one reviewer's additional absence to affect another reviewer.

Unknown references raise `ValueError`. Inputs stay unchanged and output is
sorted by reviewer ID. An empty replacement calendar or a full-span absence
removes duty while retaining reviewer identity; the engine still runs to the
horizon. A no-op replacement produces identical duty and results with the same
proposals and keyed draws. This API neither generates nor transforms arrivals.
All capacity changes are declared assumptions, not measured staffing effects.
CLI scenario configuration and persisted result contracts remain downstream
v0.1.0 work.
