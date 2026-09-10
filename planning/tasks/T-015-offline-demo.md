---
id: T-015-offline-demo
title: Ship the one-command offline synthetic demo
status: completed
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-014-experiment-artifacts
updated_at: "2026-09-10T17:27:54Z"
---

# T-015-offline-demo Ship the one-command offline synthetic demo

## Description

Ship the one-command offline demo: generate a synthetic dataset, example
assumptions, the scenario suite, model artifacts, results, and a report with no
credentials and no network access. Every major output section identifies the
data as synthetic and states that full sensitivity has not been run.

## Acceptance

- `merge-carlo demo --out out/demo --seed 42 --replications 200` succeeds on a clean checkout with no network.
- Every major output section is labeled synthetic.
- The demo report states that only the base assumption set was run.
- Rerunning with the same seed reproduces identical semantic output.

## Verification Notes

- An integration test running the demo end to end into a temporary directory.
- A test asserting no HTTP client is constructed during the demo.
- Final `mise run check`: 389 tests passed; ruff, format, mypy (34 files), and
  all commit/push/author/mutation/orb policy suites passed.
- Two credential-free, offline package-manager CLI runs at seed 42 and 200
  replications produced byte-identical nine-file bundles and 1,000 paired rows.
  Integration tests additionally forbid HTTP-client and socket construction.
- Strict TDD: missing-demo failure to green; deliberate constant-seed regression
  failed the nondefault-seed assertion, then passed after restoring forwarding.
- Workflow-v3 simplifier: no edits. Separate General, Python and Security review
  lanes, fresh candidate validation, and fresh disposition verification each
  concluded: "No concrete task-relevant findings." No fixes or deferrals.
- Scoped mutation gate retained the 80% floor: demo 221/225 killed (98.2%),
  reporting 230/243 (94.7%), CLI 2/3 (insufficient evidence below ten mutants).
  All survivors remain unsuppressed. Demo survivors change spacing or backlog
  threshold; the report warning has a surviving extra-text mutation. The CLI
  survivor is equivalent, but the decorated command itself is undiscovered.
  T-041 tracks that discovery gap for v0.1.0 release hardening, not implemented.
- Full workflow details and raw mutation results are retained in the local
  Taskrail verification artifacts for the 2026-09-10T17:27:54Z pass.

## Implementation Notes

- 2026-09-10T17:27:54Z: verification pass
