---
id: T-050-expose-structural-fit-limits-in-real-data-validation
title: Expose structural fit limits in real-data validation
status: completed
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-024-held-out-validation
updated_at: "2026-09-18T20:54:46Z"
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

- Added deterministic fit diagnostics to validation and saved combined reports:
  protocol/status, evidence flags, observed/simulated gates and cohorts,
  elapsed-delay comparison, initialization discrepancy, and the four explicit
  v0.1 structural-fit limitations. Reports retain conservative non-causal,
  non-productivity, non-safety, non-defect, and non-policy wording.
- Structural-limit metadata is required in the persisted result contract and
  must equal the complete ordered v0.1 set; omitted, partial, empty, and
  reordered values are rejected. Saved combined reports consume the validation
  artifact and do not rerun simulation.
- Verification: focused validation/experiment tests passed (55); `mise run
  check` passed (691 tests plus policy/setup guards); differential mutation
  passed with `experiment` 610/689 (88.5%), `reporting` 294/322 (91.3%), and
  `validation` 1050/1268 (82.8%). Ruff, format, mypy, and `git diff --check`
  passed. Independent General, Python, and ML/domain reviews were completed;
  all accepted findings were fixed with regression tests and final disposition
  verification found no deferred findings.
- 2026-09-18T20:54:37Z: verification pass
