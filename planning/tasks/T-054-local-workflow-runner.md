---
id: T-054-local-workflow-runner
title: Add a local real-repository workflow runner
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-27T09:57:21Z"
---

# T-054-local-workflow-runner Add a local real-repository workflow runner

## Description

Add a downloadable local runner for the documented authorized GitHub workflow.
The runner must collect and inspect one or more repositories, prepare the
data-only calibration inputs, build and persist a calibrated model, run the
persisted simulation, and summarize each repository without turning incomplete
evidence into a successful report. Fix the discovered contract mismatch where
empty descriptive empirical observations make a valid calibrated model
unloadable by `simulate`.

## Acceptance

- A local command accepts repeated repositories and explicit analysis/output
  settings, reads `GITHUB_TOKEN` without exposing it in arguments or artifacts,
  and writes separate per-repository datasets, inspection reports, model
  artifacts, experiment artifacts, and a machine-readable summary.
- Collection, inspection, Python calibration, and persisted simulation use the
  existing v0.1 interfaces; incomplete collection or invalid calibration stops
  that repository with an explicit blocked result and no fabricated report.
- A calibrated model with empty descriptive review or merge observations remains
  loadable and simulation-relevant active-effort distributions stay strictly
  validated.
- Focused tests cover successful orchestration, incomplete-collection blocking,
  secret-safe diagnostics, and the empty-observation model contract.
- Documentation provides the local command and explains the alpha-blocking
  defect and later-version evidence/modeling limitations.

## Verification Notes

- `uv run --offline --no-sync pytest tests/unit/live_workflow_test.py tests/unit/experiment_test.py -q` — 23 passed.
- `mise exec -- mise run check` — 741 passed; ruff, format, mypy, policy, and setup checks passed.
- `uv run --offline --no-sync python scripts/run_live_workflow.py --help` — command help rendered.
- Running the runner without `GITHUB_TOKEN` exited 2 with a redacted, actionable diagnostic and created no output.
- Independent disposition review resolved F-001 through F-007 and both security findings; no concrete task-relevant findings remain.
- No authorized live GitHub run was performed in this orb because no token is available.

## Implementation Notes

- 2026-09-20T20:25:01Z: verification pass
- 2026-09-27T09:57:17Z: verification pass
