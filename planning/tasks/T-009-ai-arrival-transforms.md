---
id: T-009-ai-arrival-transforms
title: Apply additive and replacement AI arrival transforms
status: completed
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-006-week-template-arrivals
updated_at: "2026-09-10T14:12:40Z"
---

# T-009-ai-arrival-transforms Apply additive and replacement AI arrival transforms

## Description

Implement the additive and replacement AI arrival transforms as typed scenario
overrides. Additive demand adds proposals equal to a declared fraction of the
baseline weekly count using one stable uniform draw per week and replication,
with stable identifiers drawn from a separately keyed template stream.
Replacement reassigns known-human proposals below a stable per-proposal
threshold, keeping timestamps and latent draws.

## Acceptance

- Adding AI demand leaves every baseline proposal identifier, timestamp, and attribute unchanged.
- Replacement preserves proposal identifiers, count, and timestamps and changes only origin and service cohort.
- Unknown and non-AI automation origins are never reassigned.
- A load sweep reuses a stable prefix of added proposals, so increasing the fraction does not resample the shared ones.
- The reported cohort mix, not only the replacement fraction, appears in the results.

## Verification Notes

- Property tests comparing baseline and transformed proposal sets.
- A test that enlarging the scenario suite does not alter an existing scenario's result.
- Executed `mise run check`: Ruff, format, mypy (19 files), 231 tests and all
  repository policy suites passed. Focused transform coverage is in
  `tests/unit/simulation/arrival_transforms_test.py` (11 tests).
- TDD: missing `AdditiveAI` import failed first; implementation passed.
  Strengthened week-variation and threshold-equality tests failed under
  deliberate missing-week-key and non-strict-threshold regressions (2 failed),
  then passed after restoring correct production behavior.
- `BASE=origin/main mise run test:mutate`: arrivals 134/142 killed, 8 survived,
  94.4% against the unchanged 80% floor; no skipped, error or timeout mutants.
  Raw `x_generate_proposals__mutmut_` survivors: 3, 7 (message variations),
  36, 40, 42, 43 (baseline purpose-key variants), 67, 74 (additive template
  purpose-key variants). No suppressions. Dataclass method discovery remains
  excluded from this score and is already tracked for v0.1.0 in T-033.
- Synthetic generator-to-FIFO manual check: baseline 4 proposals/1 AI;
  additive 0.75 yields 7/4 AI; replacement 1 yields 4/2 AI. All terminated,
  with unknown and non-AI automation remaining one each in every scenario.
- workflow-v3: dedicated code-simplifier made no changes; separate General
  and Python code-reviewer lanes, candidate validation, and fresh disposition
  verification all reported "No concrete task-relevant findings." Python
  loaded python-patterns. One review cycle; no deferred findings. Other lanes
  had no affected trust, persistence, framework or ML boundary.
- Detailed verification evidence was recorded through `taskrail verify`;
  the durable summary is retained here because generated reports are local.

## Implementation Notes

- 2026-09-10T14:12:40Z: verification pass
- Origin selects service cohort; no individual effort is inferred. The
  returned schedule exposes realized cohort counts after clipping. Shared
  constant engine service and downstream CLI artifacts remain explicit
  limitations; no second task was implemented and no new follow-up was needed.
