---
id: T-004-fifo-review-engine
title: Run a FIFO review queue with constant service to a horizon
status: completed
priority: high
spec_ref: specs/v0.1.0.md#deterministic-simulation-core
dependencies:
    - T-003-duty-calendars
updated_at: "2026-09-10T12:03:29Z"
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

- 2026-09-10T12:02:22Z: verification pass

### Workflow-v3 evidence

1. Understand: started from origin/main after T-003; reused immutable domain
   transitions and materialized UTC duty. This task is the fresh-READY,
   constant-service Python API slice. Instant successful verification and merge,
   half-open horizon, and rejected deadlines are documented; T-007/T-008 own
   loops and abandonment. No network, storage, or CLI experiment was added.
2. TDD: engine tests first failed on missing `simulation.engine`; initial
   implementation passed seven scheduling/property tests. Fractional readiness
   0.3 with service 2 then reproduced a timeout after three seconds; exact
   internal arithmetic made that regression pass with completion 2.3/service 2.
3. Initial checks: focused tests, ruff, mypy, and full pytest passed (158 tests
   before mutation-driven strengthening; final full suite is 160).
4. Dedicated Task loaded code-simplifier: no changes recommended; focused tests,
   ruff and mypy passed. No suggestions rejected.
5. Separate read-only Tasks loaded code-reviewer for General, Python, Security.
   General used ECC code-reviewer/common review rules; Python used
   python-reviewer plus python-patterns; Security used security-reviewer plus
   security-review and common security rules. Database, framework, ML and other
   domain lanes omitted: no corresponding persistence/framework/domain change.
   Three lanes fit the specialist budget. Every lane and the fresh candidate
   validator returned: "No concrete task-relevant findings."
6. No review findings to fix or defer. Mutation inspection strengthened tests
   for an ineligible first reviewer, preserved proposal/reviewer metadata,
   and duty outside the span. Deliberately changing dispatch `continue` to
   `break` failed the new test (terminal 10 != 2); restoring it passed.
7. `mise run check`: 160 tests, ruff, format, strict mypy (14 files), and all
   five shell-policy suites passed. Fresh disposition-verification Task loaded
   code-reviewer and returned "No concrete task-relevant findings." One review
   cycle; no unresolved dispositions. Manual sandbox calendar-to-engine checks
   passed all six acceptance steps; helper removed.
8. Taskrail verification passed after reviews/checks; plan/report are under
   `planning/artifacts/verify/T-004-fifo-review-engine/20260910T120222Z/`.
   Manual evidence is under
   `planning/artifacts/manual-test/T-004-fifo-review-engine/20260910T115653Z/`.
   These artifact directories are ephemeral and not committed.

### Mutation evidence and follow-ups

`BASE=HEAD mise run test:mutate` initially failed its all-module reporting step:
engine 245/262 passed but untouched calendar mutants were unexecuted (0/61).
Filed T-034-differential-mutation-scope through Taskrail for v0.1.0 release
hardening; no tooling fix implemented here. After test strengthening and actual
execution of untouched discovered modules, the unmodified command passed:
engine 254/262 (96.9%), calendars 58/61 (95.1%); CLI 2/3 has insufficient
evidence, not a passing efficacy verdict. No failures were suppressed.

Eight engine survivors remain intentionally unsuppressed: diagnostic decoration
(7,13,17,39); an interval touching the run start adds a zero-length boundary
(69); arrival at horizon is never admitted by the horizon branch (76); initial
previous time is overwritten before any assignment consumes service (101,103).
IDs refer to `x_run_fifo__mutmut_N` in this run. Dataclass-method discovery is
still limited by existing v0.1.0 task T-033; the score covers discovered engine
function mutants, not the omitted Reviewer validation method.
