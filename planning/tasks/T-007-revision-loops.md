---
id: T-007-revision-loops
title: Simulate verification and requested-change revision loops
status: todo
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-005-keyed-random-streams
updated_at: "2026-09-09T19:02:58Z"
---

# T-007-revision-loops Simulate verification and requested-change revision loops

## Description

Simulate the verification gate and the requested-change loop: an aggregate
elapsed verification delay with no runner-capacity queue, a failure leading to
an author response and a new revision, and separate first-visit and repeat
requested-change probabilities. Enforce the engine safety limit on visits and
attempts.

## Acceptance

- A run where all first reviews request changes and later reviews approve produces exactly two review visits per non-abandoned pull request.
- Verification failing once then passing produces a new revision, and no human review begins before the passing gate.
- First-visit and repeat requested-change probabilities are separately configurable and separately applied.
- Exceeding the visit or attempt limit marks the replication `engine_truncated`; it never forces a merge or masquerades as abandonment.
- A truncated replication is excluded from outcome summaries, its count is shown, and the comparison is marked incomplete.

## Verification Notes

- Deterministic mechanics fixtures with probabilities pinned to zero or one.
- A test asserting that a truncated replication disables policy ranking.

## Implementation Notes
