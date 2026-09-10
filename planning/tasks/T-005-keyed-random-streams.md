---
id: T-005-keyed-random-streams
title: Provide purpose-keyed reproducible random streams
status: completed
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-004-fifo-review-engine
updated_at: "2026-09-10T13:05:23Z"
---

# T-005-keyed-random-streams Provide purpose-keyed reproducible random streams

## Description

Provide the random stream factory: independent, reproducible NumPy generators
keyed by root seed, replication, and a purpose key of canonical strings, built
through `SeedSequence` and `Generator(PCG64(...))`. Numeric key components are
canonicalized to strings, the built-in `hash()` is never used, and common latent
variables are never keyed by scenario identifier.

## Acceptance

- The same root seed, replication, and key return an identical stream regardless of call order.
- Different purpose keys give independent streams.
- A negative seed or replication is rejected.
- No stream construction depends on `hash()` or on dictionary iteration order.

## Verification Notes

- Unit tests comparing streams across shuffled call orders.
- A test asserting that consuming one stream does not shift another.

## Implementation Notes

Workflow-v3 evidence (2026-09-10):

1. Started from origin/main at completed T-004; taskrail validate/next selected
   T-005. Scope is the stateless Python primitive, not engine integration.
2. Strict TDD: focused pytest first failed collection with ModuleNotFoundError
   for merge_carlo.simulation.randomness; after implementation all 7 cases pass.
   Tests cover identity dimensions, component boundaries, reversed request order,
   independent consumption, numeric canonicalization with Hypothesis, negative
   identity rejection, and separate processes with different PYTHONHASHSEED.
3. Initial Ruff/mypy issues in test formatting/types were corrected. Full pytest
   passed 167 tests; Ruff and strict mypy passed.
4. Dedicated code-simplifier Task loaded its skill and made no changes; focused
   pytest, Ruff and mypy passed again. No simplification suggestions accepted.
5. Independent General and Python lane Tasks loaded code-reviewer and their ECC
   reviewers (Python also python-patterns). Both concluded verbatim:
   "No concrete task-relevant findings." A fresh candidate-validation Task
   confirmed no validated or rejected IDs. Security lane omitted: no security
   use of randomness, trust boundary, secrets or external input path. Database,
   framework and other domain lanes omitted: no affected persistence/framework.
6. No findings to fix or defer. No production changes after simplification.
7. Final `mise run check` passed: 167 tests, Ruff lint/format, strict mypy
   (16 files), and all five shell guard suites. Fresh code-reviewer
   disposition-verification Task confirmed no findings and the gate blocker.
   One review cycle; no UI change. Python API exercised by focused tests.
8. Mutation gate failed: `BASE=origin/main mise run test:mutate` scored 34/39
   (87.2%) in randomness, below 90%. Survivors 7,14,24,29,34 were reviewed as
   wording-only/equivalent (details in T-035). Unexecuted modules also fail the
   aggregate due to existing T-034. No suppression, threshold reduction or
   mutation-shaped tests applied. User conditions completion/push on all gates;
   therefore verification is fail and task is blocked, not completed or pushed.

Implementation and tests: `src/merge_carlo/simulation/randomness.py` and
`tests/unit/simulation/randomness_test.py`. Follow-up T-035 explicitly applies
to v0.1.0; only filed here, not implemented. Resume T-005 after resolving its
mutation-gate decision and the existing differential-scope problem.
- 2026-09-10T12:18:16Z: verification fail
- 2026-09-10T12:18:16Z: All-gates condition unmet: mutation 34/39 (87.2%); resolve T-035 equivalent-mutant policy and T-034 differential scope before finalization/push.

### Resumed verification after T-034 and T-035

The earlier failed verification above remains historical evidence. The
maintainer approved an 80% v0.1.0 floor in T-035, and T-034 scoped differential
verdicts to executed modules. Preserved local changes were reconciled cleanly
onto origin/main at 529723c59a934bdd9360059da872e3155f64e698. The obsolete
local T-035 draft and generated STATE were not reapplied over the completed
remote tasks; Taskrail unblock/start regenerated the current execution state.
The implementation and tests are byte-identical to the reviewed first pass.

- Actual `BASE=origin/main mise run test:mutate` passed with randomness
  34/39 (87.2%) at the default 80% floor. All five survivors remain counted:
  7 wraps error wording; 14 removes default ASCII escaping; 24 changes the
  unused object separator for an array; 29 changes ASCII codec name case;
  34 removes the default big-endian argument. No mutants were suppressed.
- `mise run check` passed: 167 tests, Ruff lint/format, strict mypy (16 files),
  all five guard suites including T-034's differential scope regressions.
- A fresh code-reviewer disposition-verification Task loaded General, Python,
  and python-patterns guidance, inspected the reconciled diff and actual gate
  evidence, and confirmed: "No concrete task-relevant findings." Its verdict:
  "APPROVE — blocker resolved under the actual shipped policy and scope; no
  unresolved or newly introduced task-relevant issues."
- No findings to fix or defer; second and final verification cycle complete.
  No new follow-up filed during resumption, and no second task implemented.
  T-035, originally filed here, and existing T-034 are now completed on main.
- 2026-09-10T13:05:23Z: verification pass
