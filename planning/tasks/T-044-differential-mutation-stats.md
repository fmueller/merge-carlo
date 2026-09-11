---
id: T-044-differential-mutation-stats
title: Rebuild mutation stats for differential runs
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-11T16:07:27Z"
---

# T-044-differential-mutation-stats Rebuild mutation stats for differential runs

## Description

Release assignment: v0.1.0 release hardening, found during T-037.
`scripts/mutate-diff.sh` reuses `mutants/mutmut-stats.json` between runs.
mutmut 3.7.0 `collect_or_load_stats` profiles only new tests against a saved
cache, so an existing test that reaches a newly added function is never mapped
to it. T-037's `_replication_counts__mutmut_8/9/10` were reported as survivors
although `test_publish_complete_reproducible_bundle` kills them when run
directly. A differential verdict must not depend on a stale test mapping.

## Acceptance

- Every differential run rebuilds mutmut's test-to-function stats before
  mutating, removing only `mutants/mutmut-stats.json`, never other mutant state.
- The script's shell regression suite fails if a stale stats cache survives
  into `mutmut run`, and passes otherwise.
- The full mutation gate behavior is unchanged.

## Verification Notes

- `bash scripts/mutate-diff-test.sh` fails before the script change and passes
  after it.
- `mise run test:mutate` against a change that adds a function reached only by
  an existing test reports the mutant killed without manual cache removal.

## Implementation Notes

- 2026-09-11T16:07:27Z: verification pass
