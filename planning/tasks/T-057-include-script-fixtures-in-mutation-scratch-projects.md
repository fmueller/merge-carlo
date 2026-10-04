---
id: T-057-include-script-fixtures-in-mutation-scratch-projects
title: Include script fixtures in mutation scratch projects
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-056-reject-unrepresentable-simulation-calendar-bounds
updated_at: "2026-10-04T20:33:18Z"
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

T-057 adds `scripts/` to mutmut's `also_copy` and the existing repository-file
copy contract test. No tests, source scope, runner commands, or efficacy policy
were changed. The strengthened test failed with missing `scripts/` before the
configuration fix; release and live-workflow tests then passed (11 tests).

Workflow-v3 simplification made no edits. Independent General and Python review,
fresh candidate validation, and fresh disposition verification returned
"No concrete task-relevant findings." No findings required fixes or deferrals.

Final verification:

- `mise run check`: Ruff and format passed, strict mypy passed (60 source files),
  pytest passed (775 tests), and all commit, push, author, mutation-floor, and
  orb-setup shell guard suites passed.
- `BASE=HEAD~1 mise run test:mutate`: unmodified stock command, starting with no
  `mutants/` tree; statistics and clean tests succeeded. Scratch contains
  `scripts/run_live_workflow.py`. Selected only CLI, arrivals, and calendars;
  default floor passed: CLI 80/98 (81.6%), arrivals 174/190 (91.6%), calendars
  263/293 (89.8%). All survivors remain counted.
- From `mutants/`, `uv run --project /home/user/workspace/repo --no-sync pytest
  --collect-only -q`: 775 tests collected, including live-workflow tests.

No genuine task-local follow-ups were identified. Existing mutation discovery
limitations and their separately tracked work remain unchanged.
- 2026-10-04T20:33:18Z: verification pass
- 2026-10-04T20:33:18Z: scripts/ copied into mutation scratch; regression contract and actual fresh stock mutation workflow verified
