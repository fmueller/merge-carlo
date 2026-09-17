---
id: T-050-expose-structural-fit-limits-in-real-data-validation
title: Expose structural fit limits in real-data validation
status: todo
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-024-held-out-validation
updated_at: "2026-09-17T21:08:21Z"
---

# T-050-expose-structural-fit-limits-in-real-data-validation Expose structural fit limits in real-data validation

## Description

Make real-data validation distinguish a failed descriptive gate from a model
scope or initialization mismatch. The chronological Helm holdout was labeled
`held_out`, but the v0.1 FIFO model predicted 87.8% reviewed within 48 hours
and 100% merged within seven days versus observed 48.2% and 45.6%; the
elapsed-delay benchmark was closer on those metrics. Surface this evidence and
the unsupported workflow dimensions without diagnosing an engine bug or making
causal claims.

## Acceptance

- Validation and combined reports show protocol, observed/simulated values,
  benchmark comparison, initialization discrepancy, and the relevant evidence
  flags in a compact, deterministic fit-diagnostics section.
- The diagnostics identify unsupported v0.1 semantics such as multiple required
  approvals, reviewer routing, merge queues, and full branch protection as
  structural-fit limitations to investigate, not measured causes.
- Reports never convert a failed gate into a productivity, safety, defect, or
  policy conclusion, and retain the existing `in_sample_diagnostic` versus
  `held_out` distinction.
- Tests cover a representative mechanistic mismatch and preserve undefined and
  insufficient-evidence behavior.

## Verification Notes

- Use the saved Helm holdout evidence as a deterministic regression fixture or
  an equivalent synthetic fixture.
- Run validation/report unit tests and confirm the v0.1 offline demo remains
  unchanged.

## Implementation Notes
