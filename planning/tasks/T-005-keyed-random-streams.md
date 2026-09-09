---
id: T-005-keyed-random-streams
title: Provide purpose-keyed reproducible random streams
status: todo
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-004-fifo-review-engine
updated_at: "2026-09-09T19:02:58Z"
---

# T-005-keyed-random-streams Provide purpose-keyed reproducible random streams

## Description

Provide the random stream factory: independent, reproducible NumPy generators
keyed by root seed, replication, and a purpose key of canonical strings, built
through `SeedSequence` and `Generator(PCG64(...))`. Numeric key components are
canonicalized to strings, the built-in `hash()` is never used, and common latent
variables are never keyed by scenario identifier.

## Acceptance

- The same root seed, replication, and key return an identical stream regardless of call order.
- Different purpose keys give independent streams.
- A negative seed or replication is rejected.
- No stream construction depends on `hash()` or on dictionary iteration order.

## Verification Notes

- Unit tests comparing streams across shuffled call orders.
- A test asserting that consuming one stream does not shift another.

## Implementation Notes
