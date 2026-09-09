---
id: T-011-review-bypass
title: Simulate audited human review bypass
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-009-ai-arrival-transforms
updated_at: "2026-09-09T19:02:58Z"
---

# T-011-review-bypass Simulate audited human review bypass

## Description

Implement the hypothetical bypass scenario: an assumed eligible fraction or an
operator-supplied per-proposal label, an independently keyed audit draw
selecting the declared fraction for normal human review, and non-audited
eligible proposals skipping human review after verification passes. Eligibility
and audit draws are fixed across comparable scenarios. No risk classifier and no
real GitHub action.

## Acceptance

- An eligible fraction of zero reproduces baseline semantics under common random numbers.
- An eligible fraction of one with an audit fraction of zero consumes no human review for eligible work; only verification and coordination delay merges.
- Eligible count, audited count, merges without human review, their share of merges, and modeled review effort avoided are all reported.
- `defect_escape_rate`, `security_risk_change`, and `policy_safety` are `null` with an `unsupported_in_v0_1` reason.
- A bypassed pull request never counts as human-reviewed in a review service-level metric.

## Verification Notes

- Deterministic fixtures at both fraction extremes.
- A report test asserting the required qualification text and the null risk fields.

## Implementation Notes
