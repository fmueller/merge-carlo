---
id: T-033-dataclass-mutation-coverage
title: Cover dataclass simulation methods in mutation testing
status: blocked
priority: medium
spec_ref: specs/v0.2.0.md#mutation-discovery
dependencies:
    - T-003-duty-calendars
updated_at: "2026-09-11T10:29:17Z"
---

# T-033-dataclass-mutation-coverage Cover dataclass simulation methods in mutation testing

## Description

Release assignment: v0.2.0 (moved from v0.1.0 by maintainer decision on
2026-09-11; it no longer gates the v0.1.0 release mutation gate or publishing).

T-003's differential mutation run discovers 61 calendar mutants, all in the
top-level helpers and run-bound function. It discovers none in the decorated
dataclasses, including DutyCalendar.materialize and its absence/union logic.
The 58/61 score therefore does not establish mutation efficacy for those
methods. Restore meaningful method coverage without restructuring the model
solely for the mutation tool. Coordinate with T-030's broader efficacy gate.

## Acceptance

- Differential mutation testing discovers and executes mutations inside
  decorated simulation dataclass methods, including calendar materialization
  and lifecycle transitions.
- The per-module report cannot imply coverage of methods omitted by discovery;
  any unavoidable excluded method has an explicit limitation.
- Existing behavioral tests distinguish meaningful wrong implementations;
  equivalent mutants remain documented rather than suppressed.
- Full and differential mutation commands retain their existing scope and the
  documented runtime expectations.

## Verification Notes

- Compare `uv run mutmut results --all true` discovery before and after changes.
- Exercise `BASE=<base-ref> mise run test:mutate` and the T-030 full gate;
  record which methods were mutated, per-module efficacy, and runtime.

## Implementation Notes

Originating evidence: T-003 calendar tests and review identified the gap;
`src/merge_carlo/simulation/calendars.py` and `pyproject.toml` define the relevant
implementation and mutation configuration. This task was filed, not implemented,
as part of T-003. No dependency or architecture remedy has been chosen.

Root cause (2026-09-11): mutmut 3.7.0 `mutmut/mutation/file_mutation.py:292-293`
returns early for every decorated `ClassDef`, so no `@dataclass` body is
mutated. Upstream boxed/mutmut#480 and #558 report it; boxed/mutmut#539
(merge commit `dc58270d5234752e22247f814431750eafcf6e5f`, 2026-08-09) replaces
the class skip with a `cst.Decorator` skip. It is not in a PyPI release: the
latest is 3.7.0 (2026-07-31), and the maintainer states it ships in the next
release. Decorated functions stay skipped upstream, so `@property` methods
(for example `UTCInterval.seconds`, `RunBounds.warmup_seconds`,
`PullRequest.terminal`) will still need an explicit limitation.

Discovery evidence from `mutate_file_contents`, in memory, with no mutation run:

| Module | 3.7.0 | dc58270 | Newly discovered methods |
| --- | --- | --- | --- |
| `simulation/calendars.py` | 61 | 289 | `DutyCalendar.materialize` 131, `LocalAbsence.materialize` 24, four `__post_init__` 73 |
| `simulation/domain.py` | 0 | 341 | `PullRequest.transition` 141, `__post_init__` 106, helpers 94 |
| `simulation/engine.py` | 613 | 707 | four config `__post_init__` 78; `run_fifo`/`summarize_replications` +16 from ternary mutation (#546) |

Maintainer decision (2026-09-11): no git or local-patch remedy; wait for a PyPI
mutmut release containing #539. Runtime trampolining of `slots=True`
dataclasses, mutation efficacy, and runtime remain unverified.
- 2026-09-11T09:52:38Z: Awaiting a PyPI mutmut release containing boxed/mutmut#539 (dc58270): 3.7.0 skips all decorated class bodies (file_mutation.py:292-293). Maintainer chose no git pin or local patch. Discovery evidence in task Implementation Notes.
