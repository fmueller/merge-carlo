---
id: T-014-experiment-artifacts
title: Write experiment artifacts and the deterministic report
status: todo
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-013-metric-dictionary
updated_at: "2026-09-09T19:02:58Z"
---

# T-014-experiment-artifacts Write experiment artifacts and the deterministic report

## Description

Write the experiment artifacts and render the report: manifest, resolved
scenarios, model card, summary JSON and CSV, paired deltas, replication rows, a
Markdown report, and sampled traces. The report is a deterministic template.
Reporting reads artifacts and never reruns a simulation.

## Acceptance

- The report follows the required order: question and evidence status, scenario comparison, uncertainty and robustness, assumptions and data coverage, interpretation, reproduction.
- Monte Carlo uncertainty is reported, using a binomial interval such as Wilson for estimated event probabilities.
- The manifest carries schema, application, and model versions, content hashes, training cutoff, timezone, seed and RNG scheme, dependency versions, validation status, and the synthetic flag.
- Exported strings beginning with a spreadsheet control character are neutralized, and Markdown control text is escaped.
- Outputs are written atomically; an unrelated nonempty output directory is not overwritten without an explicit option.
- Forbidden claims about productivity, individuals, auto-approval safety, or exact future backlog never appear.

## Verification Notes

- A golden-file test on the rendered report for a fixed fixture.
- A test asserting reporting performs no simulation and no network access.

## Implementation Notes
