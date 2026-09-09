---
id: T-006-week-template-arrivals
title: Generate proposals from resampled empirical week templates
status: todo
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-005-keyed-random-streams
updated_at: "2026-09-09T19:02:58Z"
---

# T-006-week-template-arrivals Generate proposals from resampled empirical week templates

## Description

Generate baseline proposals by resampling whole empirical weeks with
replacement, preserving relative readiness times and known origin marks within a
complete local week so within-week bursts survive. Wall-clock offsets map
through the declared timezone to UTC instants. Proposal identifiers and their
latent draws are stable and independent of scenario ordering.

## Acceptance

- A sampled horizon reproduces the within-week arrival shape of its source templates.
- Proposal identifiers, timestamps, and attributes are stable for a given seed and replication.
- Fewer than eight complete training weeks yields an `exploratory_only` label rather than a silent pass.
- Attributes stay bundled inside a template rather than being independently resampled.

## Verification Notes

- Unit tests on template expansion and timezone mapping.
- A property test asserting proposal identifier stability across repeated generation.

## Implementation Notes
