---
id: T-030-mutation-floor-gate
title: Enforce the mutation efficacy floor on the simulation engine
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-013-metric-dictionary
updated_at: "2026-09-09T19:15:25Z"
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
