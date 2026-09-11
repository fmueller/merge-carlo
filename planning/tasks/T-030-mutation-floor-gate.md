---
id: T-030-mutation-floor-gate
title: Enforce the mutation efficacy floor on the simulation engine
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-013-metric-dictionary
    - T-040-artifact-validator-mutations
    - T-041-cli-command-mutations
updated_at: "2026-09-11T11:49:21Z"
---

# T-030-mutation-floor-gate Enforce the mutation efficacy floor on the simulation engine

## Description

The mutation harness is wired but has nothing to grade: the CLI skeleton
produces three mutants, below the ten-mutant minimum, so every module is
reported as insufficient evidence. Once the deterministic engine, the
scenario semantics, and the metric dictionary exist, the floor becomes a
real gate.

Confirm the floor holds on the logic-heavy modules, record any genuinely
equivalent mutant rather than silencing it, and tune the weekly run so it
finishes inside its timeout.

## Acceptance

- The engine, scenario, and metric modules each clear the per-module efficacy floor, or a surviving mutant is recorded as equivalent with the reason it cannot be distinguished.
- The floor is not met by tests written to the shape of the mutants; each new test asserts behavior the model actually specifies.
- The weekly gate completes inside its workflow timeout, and the runtime is recorded.
- `mise run test:mutate` on a logic-heavy change mutates only the touched modules and finishes fast enough for the local loop.

## Verification Notes

- Run `mise run test:mutate:gate` and record the per-module efficacy table.
- Confirm the weekly workflow run is green and its summary shows the per-module table.

## Implementation Notes

Evidence (2026-09-11) is recorded in `docs/mutation-policy.md` ("Release
mutation gate (T-030)").

Full gate: `mise run test:mutate:gate` equivalent (`uv run mutmut run`, then
`scripts/check-mutation-floor.sh`), starting from an empty `mutants/` cache.
All 22 modules clear the 80% floor. `merge_carlo.simulation.engine` 601/613
(98.0%), `merge_carlo.simulation.runner` 172/176 (97.7%),
`merge_carlo.simulation.metrics` 278/285 (97.5%). Before the new tests, engine
was 598/613 and metrics 277/285.

Survivors: 4 of the 27 first-run survivors in these modules exposed unpinned
model behavior. They are now killed by behavioral tests:
`metrics_test.py::test_first_review_completed_exactly_at_window_start_is_measured`
(finish 44),
`engine_test.py::test_probability_threshold_is_exclusive_and_random_defaults_are_zero`
(run_fifo 235) and
`bypass_test.py::test_bypass_fraction_thresholds_are_exclusive` (run_fifo 278,
291). Each test fails with its mutant applied (`uv run mutmut apply`) and passes
once the source is restored. The other 23 stay in the denominator: 13 are
equivalent and 10 change only an error message, each with its reason recorded.

Runtime on an AMD Ryzen 9 5950X with a cold cache:
- full gate: 382-383 s with 32 workers and 894 s with `--max-children 4`,
  about a sixth of the 90-minute workflow timeout, so the workflow is unchanged;
- differential `scripts/mutate-diff.sh` after an `engine.py`-only change: 224 s,
  mutating only `merge_carlo.simulation.engine`.

Not verified: the weekly GitHub workflow run was not dispatched, because pushing
the change was not requested.
- 2026-09-11T11:49:21Z: verification pass
