---
id: T-002-domain-contracts
title: Define the simulated pull request domain contracts
status: todo
priority: high
spec_ref: specs/v0.1.0.md#deterministic-simulation-core
dependencies:
    - T-001-repository-bootstrap
updated_at: "2026-09-09T19:02:58Z"
---

# T-002-domain-contracts Define the simulated pull request domain contracts

## Description

Define the typed domain contracts for a simulated pull request and its
lifecycle: identity and origin, readiness time, state, revision, first review
and terminal timestamps, review visit and requested-change and verification
counts, queue and active-service accounting, bypass flags, the abandonment
deadline, and the terminal reason. Encode the state machine transitions and the
terminal guards, without any stochastic behavior.

## Acceptance

- The pull request state and its transitions are expressed as typed contracts with no untyped dictionaries.
- A revision invalidates prior approval and verification.
- A terminal pull request cannot be revived by a later completion event.
- `unknown` origin round-trips through the contracts without being relabeled.
- At the horizon a nonterminal pull request is recorded as unresolved and censored.

## Verification Notes

- Unit tests cover every declared transition and every rejected transition.
- Property tests assert that terminal states are absorbing.

## Implementation Notes
