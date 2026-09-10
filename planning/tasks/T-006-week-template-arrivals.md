---
id: T-006-week-template-arrivals
title: Generate proposals from resampled empirical week templates
status: completed
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-005-keyed-random-streams
updated_at: "2026-09-10T13:22:17Z"
---

# T-006-week-template-arrivals Generate proposals from resampled empirical week templates

## Description

Generate baseline proposals by resampling whole empirical weeks with
replacement, preserving relative readiness times and known origin marks within a
complete local week so within-week bursts survive. Wall-clock offsets map
through the declared timezone to UTC instants. Proposal identifiers and their
latent draws are stable and independent of scenario ordering.

## Acceptance

- A sampled horizon reproduces the within-week arrival shape of its source templates.
- Proposal identifiers, timestamps, and attributes are stable for a given seed and replication.
- Fewer than eight complete training weeks yields an `exploratory_only` label rather than a silent pass.
- Attributes stay bundled inside a template rather than being independently resampled.

## Verification Notes

- Unit tests on template expansion and timezone mapping.
- A property test asserting proposal identifier stability across repeated generation.

## Implementation Notes

Workflow-v3 evidence (2026-09-10):

1. Started from requested origin/main fc307b8 with T-005 completed. Setup
   installed hooks; Taskrail validate/next selected T-006, then start ran.
   Scope: Python arrival primitive accepting caller-certified complete weeks;
   cutoff/coverage extraction remains T-022, downstream stochastic integration
   remains existing v0.1.0 work. No network, schema, CLI, or service model change.
2. Strict TDD: focused pytest failed collection with ModuleNotFoundError for
   simulation.arrivals; minimal implementation then passed 11 focused tests.
   Hypothesis exercises repeated generation across seed/replication identities
   and reordered templates; tests cover bundles, replacement, thresholds, DST,
   clipping, invalid offsets and duplicate/empty inputs.
3. Initial checks: 178 full tests, Ruff and strict mypy (18 files) passed after
   formatter corrections. Python API only; no visual UI change.
4. Dedicated Task loaded code-simplifier; no changes recommended or made.
   Focused tests, Ruff and mypy reran successfully; no rejected suggestions.
5. Parallel independent Tasks loaded code-reviewer: General with ECC general
   reviewer; Python with ECC python-reviewer and python-patterns. Security
   omitted: no external input/secret/auth boundary; Database/framework/domain
   specialists omitted: no persistence, framework or ML change. Two lanes,
   within budget. General: "No concrete task-relevant findings."
   Fresh candidate-validation Task validated sole Python candidate PY-001,
   with no duplicates or rejected candidates. Validated finding verbatim:

   FINDING PY-001 — domain
   Severity: low
   Evidence: `docs/implementation-status.md:14,32` still describes M2 as
   “keyed random streams” and says “arrival generation … remain tracked work,”
   while `src/merge_carlo/simulation/arrivals.py:48-93` now implements arrival
   generation and `tests/unit/simulation/arrivals_test.py` passes all 11
   focused tests.
   Finding: Update the implementation-status document so it no longer claims
   the newly implemented arrival generator remains unimplemented.
   Failure/impact: Readers receive contradictory implementation/readiness
   information and may incorrectly conclude T-006 has no working implementation.
   Recommended direction: Add the verified arrival-resampling primitive to
   M2/Verified and narrow the remaining-work statement to stochastic engine
   integration.
6. PY-001 fixed with task-local documentation corrections, checked against the
   implementation; no executable behavior changed, so no artificial test added.
   Mutation inspection exposed timezone-boundary coverage gaps: new New York
   and Tokyo cases deliberately regressed to host timezone both failed (0
   proposals instead of 1); restoring declared zone passed. A horizon-week
   case deliberately changed < to <= and failed with a nonexistent next-week
   DST time; restoring < passed. Production remains the reviewed implementation.
7. Final `mise run check`: 181 tests pass, Ruff lint/format, strict mypy (18
   files), all five shell guard suites. Focused arrivals: 14 pass.
   `BASE=origin/main mise run test:mutate`: arrivals 79/85 killed (92.9%),
   passes actual default 80% floor; no timeouts, suspicious or unchecked
   selected mutants. Six raw survivors remain counted: generate_proposals
   mutants 3/7 wrap error wording; 34/38/40/41 change/remove the unspecified
   purpose namespace and hence random realizations while preserving tested
   semantics. No suppression or mutation-shaped golden draw assertions.
   Decorated dataclass validators are not discovered: existing T-033 already
   applies to v0.1.0 and owns that gap; no duplicate follow-up created.
   Synthetic manual API smoke: one generated proposal passed through run_fifo,
   one merge at 32460 seconds, exploratory_only retained on the schedule.
   Evidence paths: source/test files above and docs/implementation-status.md;
   raw local logs /tmp/t006-check.log and /tmp/t006-mutation-final.log.
   Fresh disposition verification and Taskrail finalization recorded below.
8. Fresh code-reviewer disposition-verification Task loaded General, Python,
   and python-patterns guidance; approved PY-001 as resolved and concluded
   "No concrete task-relevant findings." Verified final gate logs and all
   task-local changes. One review/fix/recheck cycle; no unresolved findings
   or deferrals. Final fetch confirmed origin/main unchanged at the starting
   revision. Taskrail verify/complete follows only after this approval.
   No new follow-up tasks; T-022 and T-033 already own the v0.1.0 limitations.
- 2026-09-10T13:22:17Z: verification pass
