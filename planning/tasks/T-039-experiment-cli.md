---
id: T-039-experiment-cli
title: Wire persisted experiment simulation and reporting commands
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-023-model-builder
    - T-026-schema-export
    - T-014-experiment-artifacts
updated_at: "2026-09-13T16:04:58Z"
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

### Workflow-v3 evidence

1. Understand: `mise exec -- taskrail validate` returned `state valid`, and the
   refreshed `next --json` selection was `T-039-experiment-cli` on the active
   v0.1.0 spec. The implementation preserves artifact-only reporting, strict
   versioned input contracts, UTC execution bounds, source lineage and
   provenance, and the distinction between assumed active effort and elapsed
   review delay.
2. Strict TDD: persisted model/scenario resolution, service distributions,
   lineage checks, CLI exit behavior, atomic report output, and resource bounds
   were covered by focused tests. The final focused suite was 16 passed; the
   complete suite was 675 passed.
3. Initial and final checks: Ruff, format, strict mypy, pytest, repository
   policy suites, `git diff --check`, and the differential mutation gate passed.
4. Simplify: the dedicated workflow simplification pass completed before the
   final test-only strengthening; no unrelated abstraction or public-contract
   change was retained. The final test additions were rechecked independently
   by inspection and through the focused/full gates.
5. Independent review: separate General, Python, and Security review lanes,
   candidate validation, and disposition verification were completed for the
   implementation. The review scope covered CLI contracts, artifact atomicity,
   untrusted input/resource bounds, lineage, deterministic sampling, and the
   no-network reporting boundary.
6. Disposition: all validated task-local findings were fixed, including
   `G-001`, `G-002`, `PY-001`, `PY-002`, `PY-004`, `SEC-002`, `SEC-003`,
   `SEC-004`, and `NEW-001` through `NEW-005`. No finding was deferred.
7. Recheck: the final disposition verification found no unresolved or newly
   introduced task-relevant issue. Differential mutation results were above
   the 80% floor for every changed tracked module; the new
   `merge_carlo.experiment` module scored 602/686 (87.8%).
8. Finalization follows the completed checks: Taskrail verification and
   completion are recorded after this evidence, with commit and push performed
   only under the maintainer identity.

### Verification and limitations

- `mise run check`: 675 passed; Ruff, format, strict mypy and all shell guard
  suites passed.
- `BASE=origin/main mise run test:mutate`: every changed tracked module passed
  the 80% floor (`artifacts` 610/732, `cli` 74/90, `configuration` 111/133,
  `reporting` 289/316, `simulation.arrivals` 134/142, `simulation.engine`
  611/631, `simulation.runner` 178/183, `validation` 979/1198).
- `uv run mutmut run "merge_carlo.experiment.*"` plus the mutation-floor check:
  602/686 killed (87.8%), above the 80% floor.
- `uv run pytest -q tests/unit/experiment_test.py`: 16 passed. The tests cover
  same-seed semantic replay, invalid contracts and output protection, and
  report rendering with simulation entry points disabled.
- The existing T-033 mutation-discovery limitation remains a v0.2.0 blocker;
  it is unrelated to this v0.1.0 task and was not changed.
- 2026-09-13T16:04:48Z: verification pass
