---
id: T-027-performance-benchmark
title: Record a reproducible performance benchmark
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-025-delay-benchmark
updated_at: "2026-09-11T07:41:35Z"
---

# T-027-performance-benchmark Record a reproducible performance benchmark

## Description

Record a reproducible performance benchmark: a specified synthetic workload,
replication and scenario counts, hardware, and dependency versions, with wall
time, peak memory, event count, and output size.

## Acceptance

- The benchmark command is reproducible and its parameters are recorded with the result.
- Results are documented without stating a universal runtime promise.
- Memory stays bounded: replication rows stream and traces are sampled.
- Any decision to add parallel workers is justified by a profile, not assumed.

## Verification Notes

- Run the benchmark and record the output in the repository documentation.
- A test asserting trace retention respects the configured sampling bound.

## Implementation Notes

- 2026-09-11T07:41:35Z: verification pass
