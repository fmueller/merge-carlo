---
id: T-065-dependency-update-readiness
title: Keep dependency updates compatible with provenance snapshot tests
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-20T19:47:48Z"
---

# T-065-dependency-update-readiness Keep dependency updates compatible with provenance snapshot tests

## Description

Restore dependency PR readiness under the active release-hardening contract.
The model-card snapshot must accept supported dependency updates without losing
checks that the card records the actual runtime versions and model semantics.

## Acceptance

- Reproduce the dependency PR failures and distinguish test defects from
  dependency incompatibility or runner infrastructure failures.
- Assert actual runtime provenance separately from the stable model-card
  snapshot; retain coverage of the full remaining card and null reasons.
- Preserve immutable action pins and supported Python contracts. Merge only
  dependency updates whose required checks pass; do not publish a release.

## Verification Notes

- Run the focused calibration test before and after the fix, including a
  deliberate incorrect-provenance probe to establish test sensitivity.
- Run the full local gate and inspect each updated PR's CI matrix and diff.

## Implementation Notes

Initial evidence: PRs 15, 16 and 19 fail only the calibration model-card SHA256
snapshot, which includes installed dependency versions. PR 15 reproduced locally
with the exact CI digest. PR 17's Python 3.12 runner received a shutdown signal
during uv setup, before tests; its other Python jobs passed. PR 14 was green.
No failing assertion is tied to a GitHub Action commit hash.

Workflow evidence:

1. Read CI logs, reproduce PR 15 on its original and rebased heads, inspect
   calibration provenance/rendering and release workflow test contracts.
2. Original focused test failed with CI's exact 8185851b... digest. Replace
   presence-only version assertions with installed-metadata comparisons, then
   normalize only those version values before the full-card snapshot. Inspect
   the normalized card diff: only application/dependency values change; schema,
   feature identity, model semantics and all null reasons remain covered.
3. Focused calibration tests: 15 passed. Deliberately make calibration report
   NumPy 0.0.0-wrong using a temporary in-memory patch: the new provenance
   assertion fails; restoring the real version passes. No production edits.
4. Dedicated personal-skills:code-simplifier Task: no change; 15 tests and Ruff
   pass. General and Python code-reviewer Tasks each report: "No concrete
   task-relevant findings." No security or database implementation changes;
   workflow action pins are retained and separately checked against upstream
   release tags, without executing publishing workflows.
5. Fresh candidate-validation and disposition-verification Task reports no
   findings or unresolved concerns. No findings required fixes or deferrals.
6. Final mise run check: Ruff, formatting, strict mypy (60 files), 817 pytest
   tests and all five guard suites pass. Reviewer independently reran the same
   gate successfully. No simulation logic changes, so mutation testing is not
   applicable. Remote PR checks and merge outcomes remain a delivery gate.

The fix is carried with the Pydantic dependency PR, then inherited by rebasing
the remaining dependency branches after that PR passes CI and merges. Task
completion records implementation and local verification, not publication or
an assertion that pending remote CI already passed.
- 2026-10-20T19:47:48Z: verification pass
