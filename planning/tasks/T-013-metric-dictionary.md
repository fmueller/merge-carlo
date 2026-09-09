---
id: T-013-metric-dictionary
title: Compute the measurement window metric dictionary
status: todo
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-012-replication-runner
updated_at: "2026-09-09T19:02:58Z"
---

# T-013-metric-dictionary Compute the measurement window metric dictionary

## Description

Compute the measurement-window metric dictionary at both the all-work
operational level and the new-ready-cohort level: arrivals, merges,
abandonments, work in progress at both boundaries, review queue peak and exact
time-average length, backlog threshold exceedance, first-review and
ready-to-merge quantiles, queue wait, fixed-horizon reviewed and merged shares,
unresolved share, review utilization, requested-change count, and unreviewed
merges. Summaries are run-level.

## Acceptance

- An undefined metric is `null` with a reason such as `no_eligible_cohort`, `no_completed_reviews`, or `no_declared_review_capacity`; no denominator becomes zero silently.
- A run with no completed reviews contributes no review latency of zero.
- Fixed-horizon shares report total, eligible, and excluded counts, and arrivals near the measurement end are ineligible rather than failures.
- Each replication yields its own median and p95; the report gives the median and central 90% range of those run-level statistics.
- Conservation holds: work in progress at the end equals work in progress at the start plus arrivals minus merges minus abandonments.

## Verification Notes

- Unit tests per metric with a hand-computed fixture.
- A property test asserting the conservation identity on every valid replication.

## Implementation Notes
