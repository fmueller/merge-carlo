---
id: T-012-replication-runner
title: Run paired Monte Carlo replications across assumption sets
status: completed
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-010-capacity-scenarios
    - T-011-review-bypass
    - T-008-abandonment
updated_at: "2026-09-10T15:54:49Z"
---

# T-012-replication-runner Run paired Monte Carlo replications across assumption sets

## Description

Run the Monte Carlo experiment: for each assumption set and replication,
construct a fresh immutable parameter view and simulation state, generate the
baseline proposal schedule and its stable latent draws, apply each scenario's
declared changes without mutating the baseline, run warm-up then measurement,
and pair each scenario result with its baseline replication. Sequential
execution, streamed replication rows, opt-in sampled traces.

## Acceptance

- Scenario results pair with the matching baseline replication for paired deltas.
- Results aggregate separately per assumption set and are never pooled into one distribution.
- No worker shares mutable state or a global generator.
- Reordering scenarios or adding a new one does not change an existing scenario's result.
- The same seed in the locked reference environment reproduces identical semantic result content, excluding runtime metadata.

## Verification Notes

- A reproducibility test running the suite twice and diffing semantic results.
- A test asserting memory does not grow with replication count beyond streamed rows.

## Implementation Notes

Implemented the sequential `simulation.runner` Python API. Every scenario row
carries its matching assumption/replication baseline, measurement-window merge
count and paired delta. Continuous warm-up preserves carry-in. Immutable inputs
and purpose-keyed on-demand draws avoid shared mutable simulation/RNG state.
Summaries remain separate by assumption/scenario; partial streams and any
truncation mark comparison incomplete. Default rows omit PR diagnostics;
explicit replication indexes sample FIFO final states and boundary accounting.
Full metrics and persisted traces/reports remain T-013/T-014, not claimed here.

### Workflow-v3 evidence

1. Understand: `taskrail validate` passed and `taskrail next --json` selected
   T-012 on the requested T-011 base. Read task, active spec, arrival, calendar,
   capacity and FIFO contracts. No simulation/network boundary changed.
2. Strict TDD: initial runner tests failed collection with missing runner module;
   minimal implementation passed two pairing/reproducibility tests. A partial
   consumption test then failed (`comparison_incomplete` was false); tracking
   exhaustion fixed it. Tests use asymmetric warm-up and capacity assumptions.
3. Initial checks: Ruff/mypy passed and full pytest passed 315 tests. The memory
   test measures live allocations after collection, avoiding unrelated Python
   freelist/GC timing while testing 4 versus 100 replications.
4. Simplify: dedicated Task loaded `code-simplifier`, removed redundant copying
   of frozen assumptions and hoisted the simulation helper. Accepted both;
   focused 30 tests, Ruff and mypy passed. No rejected suggestions.
5. Independent review: separate parallel Tasks loaded `code-reviewer` in General
   and Python lanes. General used ECC code-reviewer, no companion; Python used
   ECC python-reviewer and python-patterns. General: "No concrete task-relevant
   findings." No security, database or framework lane: in-memory typed Python,
   no external trust boundary, SQL, persistence, UI or network changes. Fresh
   candidate-validation Task validated PY-001, with no rejected/duplicate items.
6. PY-001, verbatim: "`AssumptionSet` accepts `True` as one second for both
   `service_seconds` and `coordination_seconds`, despite these being duration
   parameters rather than flags." Fixed with explicit boolean rejection.
   `uv run pytest tests/unit/simulation/runner_test.py -q -k
   'invalid_service or invalid_coordination'`: three DID NOT RAISE failures
   before fix, 11 passed after. Mutation inspection also strengthened exact
   measurement-start inclusion and baseline-only identity tests: deliberate
   exclusive-start/wrong-name regressions yielded two failures, restored code
   passed. No review findings deferred.
7. Recheck: `mise run check` passed Ruff, format, strict mypy (25 files),
   pytest (320 passed) and all five shell guard suites. Focused suite: 35 passed.
   A separate synthetic API smoke run reproduced six rows twice, with fast
   deltas [0,0,0], slow deltas [1,1,1], no sampled diagnostics by default, and
   completed comparison. Fresh disposition-verification Task loaded
   `code-reviewer`, verified PY-001 and mutation dispositions, reran full checks,
   and reported "No concrete task-relevant findings." One review/fix cycle.
8. Finalization: tracked verification/completion only after those gates; commit
   and direct main push follow repository hooks and remote reconciliation.

### Scoped mutation evidence and follow-up

`BASE=11072f440ea1350327ab23e65ef16a05cd97619d mise run test:mutate` executed
runner mutants only. Final raw runner counts: 165 killed, 5 survived, 0 timeout,
0 unexecuted; 165/170 = 97.06%, above the unchanged v0.1.0 80% floor. All five
survivors remain in the denominator. Initial run was 161/170 = 94.71%.

The existing guard incorrectly reports 5/8 = 62.5%, insufficient evidence,
because it drops Unicode `ǁ` class-method names. Independent raw counting
included all 170 names, rejected any unexpected/unexecuted status and enforced
the same 80% threshold. T-038-mutation-method-reporting was filed through
Taskrail with explicit v0.1.0 applicability; its implementation is deferred to
its own task. The final reviewer independently confirmed these raw counts.
T-033 separately covers decorated dataclass validators absent from discovery.

Equivalent survivors, not suppressed: `_unique` mutants 5/6/7 change only
exception text (no exact-message contract); `ExperimentRun.__init__` mutant 2
changes private falsey exhaustion state from False to None; `_iterate` mutant
76 changes the measurement end comparison to inclusive, but the engine never
merges at the horizon. No exclusion or adjusted efficacy was applied.

Raw output is available in this worktree at
`.amp/in/artifacts/t012-raw-mutation.txt`; commands and counts above are durable
evidence. No full-repository mutation run or live integration was claimed.
- 2026-09-10T15:54:49Z: verification pass
