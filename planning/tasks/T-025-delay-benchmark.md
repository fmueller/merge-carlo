---
id: T-025-delay-benchmark
title: Compare against the elapsed-delay resampling benchmark
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-024-held-out-validation
updated_at: "2026-09-10T22:33:49Z"
---

# T-025-delay-benchmark Compare against the elapsed-delay resampling benchmark

## Description

Implement the elapsed-delay benchmark: resample historical review and completion
observations without an explicit capacity queue, applying the same cohort and
horizon accounting and preserving observed non-completion categories. Compare it
against the mechanistic baseline description.

## Acceptance

- The benchmark shares cohort and horizon definitions with the mechanistic model so the comparison is like-for-like.
- Observed non-completion categories are preserved rather than dropped.
- The comparison is reported even when the mechanistic model performs worse.
- The benchmark is labeled a descriptive reference and is never used as an intervention model.

## Verification Notes

- A fixture comparison producing both descriptions side by side.
- A test asserting the benchmark adds no capacity queue.

## Implementation Notes

- 2026-09-10T22:33:44Z: verification pass
