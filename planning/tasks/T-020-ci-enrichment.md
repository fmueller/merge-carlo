---
id: T-020-ci-enrichment
title: Enrich with optional CI check and status observations
status: todo
priority: low
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-018-cohort-collection
updated_at: "2026-09-09T19:03:11Z"
---

# T-020-ci-enrichment Enrich with optional CI check and status observations

## Description

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
