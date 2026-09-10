---
id: T-003-duty-calendars
title: Materialize timezone-aware reviewer duty calendars
status: completed
priority: high
spec_ref: specs/v0.1.0.md#deterministic-simulation-core
dependencies:
    - T-002-domain-contracts
updated_at: "2026-09-10T11:43:44Z"
---

# T-003-duty-calendars Materialize timezone-aware reviewer duty calendars

## Description

Materialize timezone-aware reviewer duty intervals ahead of a run using
`zoneinfo`, including daylight-saving transitions. Named weekly windows plus
dated absence intervals expand into concrete UTC intervals. An invalid or
ambiguous local boundary time is either resolved by a documented rule or
rejected at configuration time.

## Acceptance

- Weekly windows expand to UTC intervals across a daylight-saving transition without drifting by an hour.
- A dated absence removes the intervals it covers.
- A reviewer with no intervals is representable and is not a zero-capacity resource.
- An ambiguous or nonexistent local time is either resolved by the documented rule or rejected with a clear message.
- Horizon and warm-up are local calendar increments whose UTC bounds and exact elapsed seconds are recorded.

## Verification Notes

- Unit tests around a spring-forward and a fall-back transition in a non-UTC zone.
- A test asserting that elapsed seconds over a DST-crossing horizon are not a multiple of 86400.

## Implementation Notes

### Workflow-v3 evidence

Release assignment: v0.1.0. Selected by the repository autonomous-backlog skill
after `taskrail validate` returned `state valid` and `taskrail next --json`
selected this task with `off_spec: false`.

| Step | Evidence | Result |
| --- | --- | --- |
| 1. Understand | Active spec deterministic core/release hardening, domain dataclasses, task criteria | Offline calendar primitives only; no scheduler or config/artifact pipeline in this task |
| 2. TDD | `uv run pytest tests/unit/simulation/calendars_test.py -q` | Red: missing calendars module; green: 12 passed |
| 3. Initial checks | `mise run check`; `BASE=HEAD mise run test:mutate` | 140 tests and all guards pass; 58/61 discovered calendar mutants killed (95.1%) |
| 4. Simplify | Dedicated Task loaded code-simplifier | Cached local span boundaries, explicit overnight end date, combined prefilter; 12 focused/140 total tests, ruff/mypy pass |
| 5. Review | Separate parallel General, Python, Security Tasks loaded code-reviewer and dedicated ECC guidance; fresh candidate-validation Task | G-001 validated; no other findings, rejects, or duplicates |
| 6. Disposition | G-001 fixed with UTC possible-overlap prefilter using both folds | Regression command below: 2 expected failures before fix, 15 focused tests pass after fix |
| 7. Recheck | `mise run check`; `BASE=HEAD mise run test:mutate`; documented Python example | 143 tests and all guards pass; mutation 58/61; example UTC hours [8, 7] and horizon 687600 seconds pass |

Fresh disposition-verification Task loaded code-reviewer in General mode with
ECC/common review and testing rules. It independently reran `mise run check`
(143 tests and all guards pass), verified G-001 as RESOLVED, and concluded:
"No concrete task-relevant findings." Verdict: APPROVE. One review/fix/recheck
cycle was needed; no finding is deferred or unresolved. Step 8 finalization
uses Taskrail verify/complete after this approval; its machine-recorded
verification below is the finalization evidence.

General loaded ECC code-reviewer plus common review/testing rules. Python
loaded ECC python-reviewer and python-patterns. Security loaded ECC
security-reviewer, security-review, and common security rules. General covered
acceptance/interval semantics; Python covered datetime and typed contracts;
Security covered timezone/input boundaries. Database, framework, concurrency,
and domain-specialist lanes were omitted because no such boundary changes.
Two specialists were within the default budget.

Python and Security each concluded: "No concrete task-relevant findings."

### Validated review finding G-001 (verbatim)

FINDING G-001 — edge-case
Severity: medium
Evidence: `src/merge_carlo/simulation/calendars.py:143-160`; `tests/unit/simulation/calendars_test.py:79-91`. During Berlin’s 2026 fall-back, the UTC span `00:45–01:15` maps to naive local endpoints `02:45–02:15`. The local-time prefilter skips Sunday windows `01:00–02:00` and `02:00–02:30`, returning `()` without resolving their ambiguous boundaries.
Finding: The naive local-span overlap check can silently bypass required ambiguous-boundary rejection when a UTC span lies within the repeated fall-back hour. Existing tests use full-day spans and do not cover this reversed-wall-time case.
Failure/impact: A materialization request crossing the repeated hour may accept an ambiguous weekly boundary contrary to the documented rejection policy, potentially hiding invalid calendar data before simulation.
Recommended direction: Determine possible overlap without ordering naive local endpoints across a fold, then resolve relevant window boundaries and compare in UTC. Add a focused sub-day fall-back test asserting a clear `ambiguous local boundary ... in Europe/Berlin` error.

Disposition: fixed. `uv run pytest tests/unit/simulation/calendars_test.py -q
-k 'subday or wholly'` returned `2 failed, 1 passed, 12 deselected` before the
fix; both failures said `Failed: DID NOT RAISE ValueError`. The implementation
now filters using the earliest possible UTC start and latest possible UTC end
before strict local-boundary resolution. The full calendar file then passed
all 15 tests. The nonoverlap test preserves half-open exclusion on both sides.

### Verification limitations and follow-up

- The documented example was executed directly with Python and its assertions
  passed. There is no new CLI or visual UI behavior to test.
- Differential mutation discovery omits decorated dataclass methods. Follow-up
  T-033-dataclass-mutation-coverage is explicitly assigned to v0.1.0; it is not
  implemented here. The score describes discovered top-level functions only.
- Three surviving mutants were inspected: two add `XX` around error messages
  whose meaningful phrases are tested; the third changes `astimezone(UTC)` to
  `astimezone(None)` and is indistinguishable in this UTC orb. They are not
  suppressed or claimed to be killed. The third is environment-dependent,
  not universally equivalent.
- Calendar timezone data comes from installed zoneinfo. Scheduler integration
  and persisted configuration/result contracts remain existing backlog work.
- 2026-09-10T11:43:44Z: verification pass
