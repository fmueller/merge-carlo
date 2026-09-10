---
id: T-037-comparison-truncation-reporting
title: Propagate engine truncation through comparison artifacts and reports
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-007-revision-loops
    - T-014-experiment-artifacts
updated_at: "2026-09-10T13:37:54Z"
---

# T-037-comparison-truncation-reporting Propagate engine truncation through comparison artifacts and reports

## Description

Release assignment: v0.1.0, required before release reporting is complete.

T-007 implements the engine's truncation marker and Python aggregation gate.
The experiment/artifact/report pipeline does not exist yet. Once T-014 lands,
carry this gate through persisted comparison outputs and deterministic reports,
including comparisons where only one scenario or assumption set truncates.
This applies the truncation contract in the active spec's stochastic scenario
semantics to its experiment-runner-and-reporting outputs; it adds no new model.

## Acceptance

- A truncated replication contributes no outcome summary values, including
  merges that occurred before truncation; diagnostic replication rows retain
  its status and consumed work.
- Any truncated replication in any compared scenario or assumption set marks
  the whole comparison incomplete and disables policy ranking.
- Artifact summaries and Markdown reports expose requested, usable and
  engine-truncated replication counts prominently; zero usable runs yield
  undefined outcomes, never favorable zero counts.
- Rendering from saved artifacts preserves these decisions without rerunning
  a simulation. Existing validity gates remain independent and mandatory.

## Verification Notes

- Golden artifact/report fixture with one valid scenario and one truncated
  scenario, including earlier merges inside the truncated diagnostic.
- All-truncated and mixed-assumption-set fixtures; assert no ranking and no
  simulation or network calls during rendering.

## Implementation Notes

Filed through Taskrail during T-007; not implemented in that task. Coordinate
with T-012/T-013/T-014 rather than introducing a second aggregation pipeline.
