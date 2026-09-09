---
id: T-019-readiness-and-origin
title: Resolve readiness basis and work origin attribution
status: todo
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-018-cohort-collection
updated_at: "2026-09-09T19:03:11Z"
---

# T-019-readiness-and-origin Resolve readiness basis and work origin attribution

## Description

Resolve readiness basis and work origin. Readiness is `observed_event`,
`supported_reconstruction`, `created_at_proxy`, or `unknown`, with strict as the
default policy and the created-at proxy available only through an explicit
option recorded in every model and report. Actor kind and work origin stay
separate concepts, an operator-supplied actor-to-origin mapping is supported,
and conflicts resolve deterministically with the basis recorded.

## Acceptance

- A non-draft latest snapshot does not imply the pull request was originally non-draft.
- Unknown readiness is excluded from ready-based calibration rather than replaced with zero draft time.
- Reopened pull requests and repeated draft/ready lifecycles are excluded from the mechanistic-fit cohort but remain in totals with the excluded fraction shown.
- A bot account is not classified as an AI coding agent, and `unknown` origin survives into exports unless an explicit hypothetical mapping is present.
- No AI detector is trained and no `ai_generated_ratio` is estimated.

## Verification Notes

- Fixture tests with draft-to-ready evidence, unknown readiness, reopened pull requests, and null authors.
- A test asserting all-unknown origin stays unknown in exports.

## Implementation Notes
