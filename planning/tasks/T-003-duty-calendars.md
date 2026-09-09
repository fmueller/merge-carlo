---
id: T-003-duty-calendars
title: Materialize timezone-aware reviewer duty calendars
status: todo
priority: high
spec_ref: specs/v0.1.0.md#deterministic-simulation-core
dependencies:
    - T-002-domain-contracts
updated_at: "2026-09-09T19:02:58Z"
---

# T-003-duty-calendars Materialize timezone-aware reviewer duty calendars

## Description

Materialize timezone-aware reviewer duty intervals ahead of a run using
`zoneinfo`, including daylight-saving transitions. Named weekly windows plus
dated absence intervals expand into concrete UTC intervals. An invalid or
ambiguous local boundary time is either resolved by a documented rule or
rejected at configuration time.

## Acceptance

- Weekly windows expand to UTC intervals across a daylight-saving transition without drifting by an hour.
- A dated absence removes the intervals it covers.
- A reviewer with no intervals is representable and is not a zero-capacity resource.
- An ambiguous or nonexistent local time is either resolved by the documented rule or rejected with a clear message.
- Horizon and warm-up are local calendar increments whose UTC bounds and exact elapsed seconds are recorded.

## Verification Notes

- Unit tests around a spring-forward and a fall-back transition in a non-UTC zone.
- A test asserting that elapsed seconds over a DST-crossing horizon are not a multiple of 86400.

## Implementation Notes
