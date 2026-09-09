---
id: T-024-held-out-validation
title: Run held-out descriptive validation with evidence gates
status: todo
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-023-model-builder
updated_at: "2026-09-09T19:03:12Z"
---

# T-024-held-out-validation Run held-out descriptive validation with evidence gates

## Description

Run held-out descriptive validation on a chronological split with the model
frozen before outcomes are inspected. Replay held-out arrival timestamps while
simulating downstream review and completion, using only attributes known at the
replay time. Compare the two mature fixed-horizon shares, completion-conditioned
median first-review elapsed time, and weekly merge counts against configurable
tolerances.

## Acceptance

- A validation interval overlapping parameter fitting is rejected unless explicitly marked an in-sample diagnostic.
- The result is one of pass, fail, or `insufficient_evidence`; too small a held-out cohort yields insufficient evidence rather than a verdict.
- Exact observed and simulated values, cohort sizes, and variability are output even when a gate passes.
- `validate --strict` exits with code 4 when its declared criteria fail; an exploratory report with warnings still succeeds.
- A baseline fit is never labeled causally validated or safe for auto-approval.
- Initialization discrepancy is reported, and absolute backlog forecasting is not passed where that discrepancy is material.

## Verification Notes

- Fixture tests for each of pass, fail, and insufficient evidence.
- An exit-code test for `validate --strict`.

## Implementation Notes
