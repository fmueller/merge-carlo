---
id: T-022-feature-builder
title: Build leakage-checked features at a frozen training cutoff
status: completed
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-021-dataset-inspection
updated_at: "2026-09-10T20:24:24Z"
---

# T-022-feature-builder Build leakage-checked features at a frozen training cutoff

## Description

Build features at a frozen training cutoff with temporal leakage rejected: ready
arrivals per complete local week, first substantive human review elapsed time,
first observed decision, requested-change prevalence with its denominator and
horizon, merge-conditioned ready-to-merge elapsed time, fixed-horizon outcomes
for mature cohorts, size snapshots as descriptive metadata, and validly
attributed CI observations.

## Acceptance

- A substantive review is a first non-author, declared-human approval or changes-requested submission after readiness.
- Pending review drafts are not counted as submitted reviews; comment-only reviews are counted separately.
- Final size snapshots and later labels cannot leak into a feature computed at an earlier cutoff.
- Ready-to-merge elapsed time is labeled completion-conditioned and never presented as an uncensored population distribution.
- Requested-change prevalence is never labeled a defect rate.

## Verification Notes

- Leakage tests that fail if any post-cutoff attribute reaches a feature.
- Unit tests per feature against a hand-computed fixture.

## Implementation Notes

- 2026-09-10T20:24:13Z: verification pass
