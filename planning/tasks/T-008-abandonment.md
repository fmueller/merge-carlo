---
id: T-008-abandonment
title: Resolve abandonment as an exogenous competing event
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-007-revision-loops
updated_at: "2026-09-09T19:02:58Z"
---

# T-008-abandonment Resolve abandonment as an exogenous competing event

## Description

Model abandonment as an exogenous competing event: a declared deadline
probability and a positive elapsed-time distribution sampled at pull request
entry. Reaching the deadline cancels future work and releases review occupancy,
counting only the service actually consumed. A deadline after a merge has no
effect, and a deadline at or before a candidate completion wins over that
completion.

## Acceptance

- Abandonment during active review counts only consumed service, releases the reviewer, and prevents any later completion from merging the pull request.
- A deadline later than an achieved merge changes nothing.
- A deadline coinciding with a merge time resolves to abandonment, deterministically.
- Closed-without-merge outcomes remain in reporting rather than being dropped as unexplained.

## Verification Notes

- Deterministic fixtures for each ordering of deadline and completion.
- A conservation test that abandoned work still balances the ledger.

## Implementation Notes
