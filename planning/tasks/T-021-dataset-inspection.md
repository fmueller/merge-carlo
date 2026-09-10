---
id: T-021-dataset-inspection
title: Report dataset coverage and quality from inspect
status: completed
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-019-readiness-and-origin
updated_at: "2026-09-10T19:55:03Z"
---

# T-021-dataset-inspection Report dataset coverage and quality from inspect

## Description

Report dataset coverage and quality from `inspect`: counts, date coverage,
missingness, censoring, origin attribution coverage, exclusions, and extraction
limitations, in Markdown and machine-readable form.

## Acceptance

- The report states endpoint coverage status per collection family.
- Readiness basis and origin attribution distributions are shown, including the unknown fractions.
- Excluded lifecycle fractions and their reasons are shown.
- Nothing in the report converts a missing permission or truncated collection into an empty, complete history.

## Verification Notes

- A golden-file test on a fixture dataset with deliberate partial coverage.
- A test asserting no identifying free text reaches the report.

## Implementation Notes

- 2026-09-10T19:54:50Z: verification pass
