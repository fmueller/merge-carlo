---
id: T-010-capacity-scenarios
title: Apply review calendar overrides and reviewer absences
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-009-ai-arrival-transforms
updated_at: "2026-09-10T14:55:11Z"
---

# T-010-capacity-scenarios Apply review calendar overrides and reviewer absences

## Description

Support review capacity scenarios: a calendar override that replaces a named
calendar completely, and dated reviewer absences expressed as half-open
intervals in the configured local timezone unless an explicit offset is given.
The arrival process is untouched unless another change is separately declared.

## Acceptance

- A calendar override replaces the named calendar rather than merging into it.
- An absence interval is half-open and removes exactly the covered duty intervals.
- Removing a reviewer entirely leaves a runnable model with reduced capacity.
- A no-op override reproduces the baseline result exactly under common random numbers.

## Verification Notes

- Unit tests on override resolution and absence expansion.
- A controlled FIFO fixture with constant service and no loops where added capacity does not worsen completion.

## Implementation Notes

Implemented the Python capacity primitive; CLI configuration/artifact wiring
remains existing downstream v0.1.0 work. No second task was implemented.

### Workflow evidence

1. Validated state and deterministic next selection from origin/main; read
   task/spec, calendar primitives and FIFO contracts before implementation.
2. Strict TDD: calendar tests initially had three expected failures rejecting
   explicit offsets; capacity tests failed collection on the missing module.
   Minimal implementation passed the full suite (265 tests).
3. Initial Ruff, mypy and pytest passed. Capacity fixtures cover complete
   replacement, individual absence isolation, stable no-op keyed results,
   unknown references, zero duty and hand-calculated added-capacity completion.
4. Dedicated code-simplifier loaded its skill and recommended no edits;
   focused tests passed (23).
5. Parallel General and Python reviewers loaded code-reviewer and dedicated
   guidance (Python also python-patterns). No security/database lane: no
   loader, network, auth or persistence change. Fresh candidate validation
   confirmed G-001 and PY-001 as distinct.
6. G-001: "`LocalAbsence` accepts named-zone aware datetimes as though they
   carried an explicit offset, allowing an ambiguous DST boundary to be
   silently selected despite the task and documentation permitting ambiguity
   resolution only through an explicit offset."
   PY-001: "`LocalAbsence.materialize()` misclassifies datetimes with a non-null
   but non-offset-producing `tzinfo`, causing `astimezone()` to apply the orb’s
   host timezone rather than the configured calendar timezone."
   Both fixed by rejecting tzinfo other than None or datetime.timezone.
   Four endpoint regressions failed with DID NOT RAISE, then passed.
7. Fresh disposition review confirmed both fixes and found PY-002:
   "The newly added regression fixture violates the repository’s strict typing
   gate because its `tzinfo` subclass does not implement all abstract methods."
   Mypy reproduced the missing dst/tzname error; typed fixture methods fixed
   it. Second/final fresh disposition review resolved all three findings:
   "No concrete task-relevant findings." No deferrals.
8. Final `mise run check`: Ruff lint/format, strict mypy (21 files), 269 tests,
   and all commit/push/author/mutation-floor/orb-setup policy suites passed.
   `git diff --check` passed. Taskrail finalization follows these gates.

### Manual and mutation evidence

Manual Python API smoke: baseline and no-op each merge three proposals at
33000, 33600, 34200 seconds, consuming 1800 active / 3600 duty seconds.
An empty override leaves all three unresolved at 86400, with zero active/duty.
The controlled two-reviewer test completes at 33000, 33000, 33600 seconds.

`BASE=origin/main mise run test:mutate` passed twice, retaining the 80% floor:
calendars 58 killed / 61 discovered (95.1%), capacity 37/40 (92.5%). Raw scoped
totals: 101 tested, 95 killed, 6 survived, zero timeout/suspicious/skipped.
No mutants suppressed. Calendar survivors are existing
`x__local_to_utc__mutmut_3`, `x__local_to_utc__mutmut_9`, and
`x_materialize_run_bounds__mutmut_8`. Capacity survivors
`x_materialize_reviewers__mutmut_7`, `_11`, `_16` only add XX decoration to
error messages; unknown references still raise the documented ValueError.
Exact error-message decoration is not a public contract.

The current mutation tool omits decorated dataclass methods, including the
changed absence methods. This score does not establish their mutation
coverage. Existing T-033 explicitly owns this v0.1.0 release-hardening gap;
behavioral offset/DST/half-open/property tests still execute those methods.
No new follow-up was needed or filed. Raw execution logs during this run:
`/tmp/t010-mutation-final.log`, `/tmp/t010-check-final.log`; durable decisive
results and discovery limitation are recorded here.
- 2026-09-10T14:55:10Z: verification pass
