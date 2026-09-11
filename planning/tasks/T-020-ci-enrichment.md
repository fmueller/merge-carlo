---
id: T-020-ci-enrichment
title: Enrich with optional CI check and status observations
status: todo
priority: low
spec_ref: specs/v0.2.0.md#ci-enrichment
dependencies:
    - T-018-cohort-collection
updated_at: "2026-09-11T10:31:03Z"
---

# T-020-ci-enrichment Enrich with optional CI check and status observations

## Description

Release assignment: v0.2.0 (moved from v0.1.0 by maintainer decision on
2026-09-11; v0.1.0 ships without CI enrichment).

Optionally enrich with check-run and commit-status metadata for known, correctly
attributed commit SHAs, preserving attempt and completeness information. An
unavailable CI endpoint must not prevent a core dataset, but it disables
CI-derived estimates.

## Acceptance

- Missing checks are recorded as unknown, never as successful.
- Checks on different SHAs, merge-test SHAs, or reruns are not merged into one timeless result.
- A legacy status without a start event yields no runtime measurement.
- A permission-denied CI endpoint yields `unavailable` and still produces a complete core dataset with CI-derived estimates disabled.

## Verification Notes

- Fixture tests for permission-denied checks and for multi-attempt runs.
- A test that a green final snapshot does not produce a first-attempt failure probability.

## Implementation Notes
