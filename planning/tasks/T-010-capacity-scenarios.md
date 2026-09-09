---
id: T-010-capacity-scenarios
title: Apply review calendar overrides and reviewer absences
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-009-ai-arrival-transforms
updated_at: "2026-09-09T19:02:58Z"
---

# T-010-capacity-scenarios Apply review calendar overrides and reviewer absences

## Description

Support review capacity scenarios: a calendar override that replaces a named
calendar completely, and dated reviewer absences expressed as half-open
intervals in the configured local timezone unless an explicit offset is given.
The arrival process is untouched unless another change is separately declared.

## Acceptance

- A calendar override replaces the named calendar rather than merging into it.
- An absence interval is half-open and removes exactly the covered duty intervals.
- Removing a reviewer entirely leaves a runnable model with reduced capacity.
- A no-op override reproduces the baseline result exactly under common random numbers.

## Verification Notes

- Unit tests on override resolution and absence expansion.
- A controlled FIFO fixture with constant service and no loops where added capacity does not worsen completion.

## Implementation Notes
