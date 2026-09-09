---
id: T-015-offline-demo
title: Ship the one-command offline synthetic demo
status: todo
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-014-experiment-artifacts
updated_at: "2026-09-09T19:02:58Z"
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

## Implementation Notes
