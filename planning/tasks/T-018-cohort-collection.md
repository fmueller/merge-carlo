---
id: T-018-cohort-collection
title: Collect and reconcile the pull request cohort
status: todo
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-017-projected-store
updated_at: "2026-09-09T19:03:11Z"
---

# T-018-cohort-collection Collect and reconcile the pull request cohort

## Description

Collect and reconcile the historical cohort: enumerate pull requests in all
states plus all currently open ones, union by immutable identifier, include both
pull requests created inside the analysis interval and older ones open during
it, fetch child collections completely, and deduplicate because the repository
changes while extraction runs. Store the analysis interval, retrieval time, and
source event or snapshot time separately.

## Acceptance

- Old inactive open pull requests are captured even though an update-time cutoff would omit them.
- Closed-without-merge and still-open pull requests are retained, so arrivals are not biased toward fast completions.
- Every collection carries `complete`, `partial`, `unavailable`, or `not_requested`; a safety limit yields `partial`, never a falsely complete dataset.
- `collect --resume` resumes through a reconciliation pass rather than a saved page offset, and an interrupted run leaves either partial data marked incomplete or the previous complete artifact.
- A later snapshot is stored with its observation time and never used as if known earlier.

## Verification Notes

- Fixture tests with changed page order, duplicate rows, old open pull requests, and a partially interrupted extraction.
- A test that a future snapshot attribute cannot leak into a historical feature cutoff.

## Implementation Notes
