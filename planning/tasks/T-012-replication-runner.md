---
id: T-012-replication-runner
title: Run paired Monte Carlo replications across assumption sets
status: todo
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-010-capacity-scenarios
    - T-011-review-bypass
    - T-008-abandonment
updated_at: "2026-09-09T19:02:58Z"
---

# T-012-replication-runner Run paired Monte Carlo replications across assumption sets

## Description

Run the Monte Carlo experiment: for each assumption set and replication,
construct a fresh immutable parameter view and simulation state, generate the
baseline proposal schedule and its stable latent draws, apply each scenario's
declared changes without mutating the baseline, run warm-up then measurement,
and pair each scenario result with its baseline replication. Sequential
execution, streamed replication rows, opt-in sampled traces.

## Acceptance

- Scenario results pair with the matching baseline replication for paired deltas.
- Results aggregate separately per assumption set and are never pooled into one distribution.
- No worker shares mutable state or a global generator.
- Reordering scenarios or adding a new one does not change an existing scenario's result.
- The same seed in the locked reference environment reproduces identical semantic result content, excluding runtime metadata.

## Verification Notes

- A reproducibility test running the suite twice and diffing semantic results.
- A test asserting memory does not grow with replication count beyond streamed rows.

## Implementation Notes
