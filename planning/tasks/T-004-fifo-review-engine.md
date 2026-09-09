---
id: T-004-fifo-review-engine
title: Run a FIFO review queue with constant service to a horizon
status: todo
priority: high
spec_ref: specs/v0.1.0.md#deterministic-simulation-core
dependencies:
    - T-003-duty-calendars
updated_at: "2026-09-09T19:02:58Z"
---

# T-004-fifo-review-engine Run a FIFO review queue with constant service to a horizon

## Description

Run the deterministic engine: a central FIFO queue ordered by
`(queue_entered_at, pr_id, revision)`, reviewers taking the oldest pull request
they may review, no self-review, stable tie-breaking on reviewer identifier, and
constant service consumed only inside duty intervals with pause and resume
across shift boundaries. Event-scheduled, never a per-minute loop, and bounded
by a finite horizon.

## Acceptance

- Two pull requests ready at time zero with one always-available reviewer and 600-second service complete at 600 and 1200 seconds, with 1200 seconds of active service.
- The same fixture with two eligible reviewers completes both at 600 seconds.
- A review needing 120 active minutes with 60 minutes left in the window consumes exactly 60 today and resumes in the next window; overnight time is not active effort.
- With no reviewer duty intervals no human-reviewed merge occurs, queued work stays unresolved, and the run ends at the horizon without hanging.
- A self-authored pull request with only its author available is never reviewed and the limitation is reported.
- Conservation holds at every tracked event boundary and at the horizon.

## Verification Notes

- Hand-calculated scheduling fixtures as unit tests.
- A property test asserting nonnegative waits, monotonic event times, and utilization at most one.

## Implementation Notes
