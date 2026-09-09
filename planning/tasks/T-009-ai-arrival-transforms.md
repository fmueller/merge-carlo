---
id: T-009-ai-arrival-transforms
title: Apply additive and replacement AI arrival transforms
status: todo
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-006-week-template-arrivals
updated_at: "2026-09-09T19:02:58Z"
---

# T-009-ai-arrival-transforms Apply additive and replacement AI arrival transforms

## Description

Implement the additive and replacement AI arrival transforms as typed scenario
overrides. Additive demand adds proposals equal to a declared fraction of the
baseline weekly count using one stable uniform draw per week and replication,
with stable identifiers drawn from a separately keyed template stream.
Replacement reassigns known-human proposals below a stable per-proposal
threshold, keeping timestamps and latent draws.

## Acceptance

- Adding AI demand leaves every baseline proposal identifier, timestamp, and attribute unchanged.
- Replacement preserves proposal identifiers, count, and timestamps and changes only origin and service cohort.
- Unknown and non-AI automation origins are never reassigned.
- A load sweep reuses a stable prefix of added proposals, so increasing the fraction does not resample the shared ones.
- The reported cohort mix, not only the replacement fraction, appears in the results.

## Verification Notes

- Property tests comparing baseline and transformed proposal sets.
- A test that enlarging the scenario suite does not alter an existing scenario's result.

## Implementation Notes
