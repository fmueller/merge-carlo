---
id: T-039-experiment-cli
title: Wire persisted experiment simulation and reporting commands
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-023-model-builder
    - T-026-schema-export
    - T-014-experiment-artifacts
updated_at: "2026-09-10T16:54:27Z"
---

# T-039-experiment-cli Wire persisted experiment simulation and reporting commands

## Description

Release assignment: v0.1.0, required before the documented real-data pipeline
is complete. T-014 supplies Python artifact publication and artifact-only
rendering, but no existing task explicitly owns the README's `simulate` and
`report` command integration. Connect those commands to the model/configuration
contracts after T-023/T-026. T-015 continues to own only the offline demo.

Follow-up derived from T-014-experiment-artifacts's verification or discovery.

## Acceptance

- `simulate --model ... --scenarios ... --out ...` resolves validated model and
  scenario artifacts, propagates source dataset/model lineage and parameter
  provenance, and publishes the versioned experiment bundle.
- `report --results ... --validation ... --out ...` reads saved artifacts and
  validation results without a simulation or network call; it writes atomically
  and preserves conditional language and evidence status.
- Invalid versions, unknown keys and incompatible input contracts fail with
  documented structured errors and exit codes. Nonempty output protection has
  an explicit user-visible override.
- The documented reproduction procedure is executable from persisted inputs,
  including unambiguous additive/replacement demand semantics and UTC bounds;
  no manual Python dataclass reconstruction is needed in the CLI workflow.

## Verification Notes

- Fixture-backed end-to-end CLI run, saved-artifact re-render with simulation and
  network entry points disabled, same-seed semantic replay, invalid-contract and
  overwrite protection tests. Include actual dependency/source hash lineage.

## Implementation Notes

Not implemented in T-014. Expanded truncation-count presentation remains T-037;
do not introduce a second aggregation or report pipeline.
