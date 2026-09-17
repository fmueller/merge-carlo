---
id: T-049-correct-calibration-workflow-documentation
title: Correct v0.1 calibration workflow documentation
status: todo
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-17T21:08:15Z"
---

# T-049-correct-calibration-workflow-documentation Correct v0.1 calibration workflow documentation

## Description

Make the v0.1 command documentation match the shipped interface. The README
currently presents `merge-carlo calibrate`, although calibration is a Python
API. Replace that invocation with a runnable API example and the persisted
`collect`/`inspect`, `validate`, `simulate`, and `report` pipeline without
expanding the v0.1 CLI contract.

## Acceptance

- No v0.1 documentation or example invokes a nonexistent `calibrate` CLI.
- The documented Python calibration example names its inputs, output artifacts,
  and the subsequent supported CLI commands accurately.
- A documentation smoke check runs the copied command sequence against fixture
  or synthetic artifacts and confirms the documented exit-code behavior.
- The documentation continues to state that real-data calibration and live
  GitHub integration require authorized inputs and are not implied by fixture
  tests.

## Verification Notes

- Search documentation for stale `merge-carlo calibrate` invocations.
- Run the documented offline sequence and the CLI help check.

## Implementation Notes
