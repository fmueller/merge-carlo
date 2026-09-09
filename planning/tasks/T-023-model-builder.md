---
id: T-023-model-builder
title: Calibrate a provenance-tagged model and model card
status: todo
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies:
    - T-022-feature-builder
updated_at: "2026-09-09T19:03:11Z"
---

# T-023-model-builder Calibrate a provenance-tagged model and model card

## Description

Calibrate an empirically informed model: freeze the cutoff, build descriptive
distributions, arrival templates, and coverage, merge the explicitly supplied
assumptions, validate parameter domains and units, and emit the model, a
calibration record, and a model card. Every parameter carries a provenance basis
and its evidence metadata. No optimizer infers reviewer effort from latency.

## Acceptance

- Missing required assumptions fail with a useful message rather than a silent default.
- Every parameter records value specification, unit, basis, sample count, missingness treatment, and any grouping or fallback rule.
- A hand-entered assumption carries no confidence interval unless it is itself a declared assumption distribution.
- The readiness policy in force is recorded in the model and the report.
- Weak empirical support yields an `exploratory_only` label rather than an unqualified model.
- A lognormal is specified by median and log-space sigma; an ambiguous mean-and-sigma configuration is rejected.

## Verification Notes

- Unit tests for each evidence flag threshold.
- A test asserting the model card renders every unavailable quantity as null with a reason.

## Implementation Notes
