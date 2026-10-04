---
id: T-057-include-script-fixtures-in-mutation-scratch-projects
title: Include script fixtures in mutation scratch projects
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-056-reject-unrepresentable-simulation-calendar-bounds
updated_at: "2026-10-04T20:06:20Z"
---

# T-057-include-script-fixtures-in-mutation-scratch-projects Include script fixtures in mutation scratch projects

## Description

The differential mutation runner cannot collect the current test suite in its
scratch project: `tests/unit/live_workflow_test.py` imports
`scripts.run_live_workflow`, but `tool.mutmut.also_copy` omits `scripts/`.
Restore the documented mutation gate under Release Hardening without relying
on manually copied scratch files or weakening test collection.

Follow-up derived from T-056-reject-unrepresentable-simulation-calendar-bounds's verification or discovery.

## Acceptance

- A fresh mutation scratch project includes the script fixtures needed by the
  current suite; statistics collection does not fail with `No module named 'scripts'`.
- Differential mutation testing retains its changed-module scope and efficacy
  policy; no tests are excluded to hide collection failures.

## Verification Notes

- Reproduced during T-056 with `BASE=origin/main mise run test:mutate`:
  `mutants/tests/unit/live_workflow_test.py:15` raises
  `ModuleNotFoundError: No module named 'scripts'`, then statistics collection
  fails. Supplying `PYTHONPATH` did not resolve it. Manually copying `scripts/`
  into the disposable `mutants/` tree allowed collection to proceed.

## Implementation Notes

Follow-up only; no production or mutation configuration change in T-056.
