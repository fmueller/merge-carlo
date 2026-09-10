---
id: T-013-metric-dictionary
title: Compute the measurement window metric dictionary
status: completed
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-012-replication-runner
updated_at: "2026-09-10T16:24:03Z"
---

# T-013-metric-dictionary Compute the measurement window metric dictionary

## Description

Compute the measurement-window metric dictionary at both the all-work
operational level and the new-ready-cohort level: arrivals, merges,
abandonments, work in progress at both boundaries, review queue peak and exact
time-average length, backlog threshold exceedance, first-review and
ready-to-merge quantiles, queue wait, fixed-horizon reviewed and merged shares,
unresolved share, review utilization, requested-change count, and unreviewed
merges. Summaries are run-level.

## Acceptance

- An undefined metric is `null` with a reason such as `no_eligible_cohort`, `no_completed_reviews`, or `no_declared_review_capacity`; no denominator becomes zero silently.
- A run with no completed reviews contributes no review latency of zero.
- Fixed-horizon shares report total, eligible, and excluded counts, and arrivals near the measurement end are ineligible rather than failures.
- Each replication yields its own median and p95; the report gives the median and central 90% range of those run-level statistics.
- Conservation holds: work in progress at the end equals work in progress at the start plus arrivals minus merges minus abandonments.

## Verification Notes

- Unit tests per metric with a hand-computed fixture.
- A property test asserting the conservation identity on every valid replication.

## Implementation Notes

Implemented for v0.1.0 through workflow-v3 and autonomous-backlog. The Python
runner emits all-work and new-ready metric dictionaries without enabling traces.
`docs/limitations.md#measurement-dictionary` defines boundaries, populations,
queue/service accounting, latency conditioning, horizon eligibility and summary
semantics. Persisted reports and binomial intervals remain T-014's scope.

### Workflow evidence

1. Confirmed the requested origin/main base with T-012 completed; Taskrail
   validation and deterministic selection chose T-013, then started it via CLI.
2. Strict TDD: the new metric fixture failed collection with
   `ModuleNotFoundError: No module named 'merge_carlo.simulation.metrics'`.
   After implementation, four initial metric tests passed. Runner integration
   first failed with `AttributeError: 'RunCounts' object has no attribute
   'metrics'`, then passed with dictionaries attached to streamed rows.
3. Initial whole-suite checks passed (324 tests), followed by hand-computed
   boundary, abandonment, repeat-review, bypass, off-duty and censoring cases.
   Conservation uses Hypothesis across arrivals, service, window starts and
   stochastic abandonment, checking both populations.
4. A dedicated code-simplifier subagent consolidated active-duty assignment
   selection in the engine. The diff was inspected; 54 metric/runner tests and
   82 engine tests passed afterward. No suggestions were rejected.
5. Independent read-only General and Python lane subagents loaded code-reviewer
   and their mapped ECC reviewers; Python also loaded python-patterns. Each
   returned verbatim: "No concrete task-relevant findings." A fresh candidate
   validator confirmed an empty candidate set, with no rejected/deduplicated IDs.
   Security, database and framework lanes were omitted because no network,
   auth, persistence, framework or UI behavior changed; no budget exception.
6. No review findings required fixing or deferral. Raw mutation inspection
   prompted stronger undefined-reason and exact-start tests. Deliberately
   changing `>= start` to `> start` in interval cohort selection made the
   exact-start test fail; restoring the correct comparison passed all 20 metric
   tests. No production behavior was changed to satisfy a mutant score.
7. Fresh code-reviewer disposition verification returned verbatim:
   "No concrete task-relevant findings." It checked the strengthened tests;
   55 metric/runner tests, Ruff, strict mypy and diff checks passed. One review
   cycle sufficed. `mise run check` passed all 340 tests, lint, formatting,
   types and five guard suites. A manual synthetic Python run gave arrivals 3,
   merges 2, start/end WIP 1/2, queue integral 12 PR-seconds and average 0.8.
8. Tracked finalization uses taskrail verify and complete only after these
   reviews and gates. Exactly one task is implemented in this change.

### Mutation evidence

`BASE=origin/main mise run test:mutate` executed only the three changed source
modules, then reran after simplification. `uv run mutmut run
'merge_carlo.simulation.metrics.*'` reran metrics after strengthening tests.
Final raw counts, including mangled class methods, are:

| Module | Killed | Timeout | Survived | Total | Raw efficacy |
| --- | ---: | ---: | ---: | ---: | ---: |
| engine | 595 | 3 | 15 | 613 | 97.55% |
| metrics | 276 | 0 | 9 | 285 | 96.84% |
| runner | 172 | 0 | 4 | 176 | 97.73% |

Every selected mutant executed. All modules pass v0.1.0's 80% floor; no
equivalence exclusions or status rewrites were applied. The existing guard
omits Unicode-mangled class methods (already filed as T-038, v0.1.0 before the
release gate), so an independent raw-name tally asserted execution and the
floor per module. The guard itself also exited successfully, but its metrics
32/32 and runner 5/8 displays are incomplete and are not the reported efficacy.
The table preserves raw counts; full local output comes from
`uv run mutmut results --all true` and is retained with verification evidence.
Dataclass instrumentation remains the separately tracked T-033 limitation.

No new follow-up tasks were filed: T-014 owns persisted reporting, and T-038
already owns the rediscovered parser defect. Both remain v0.1.0 work; neither
was implemented here. Recommended next task: T-014-experiment-artifacts.
- 2026-09-10T16:24:03Z: verification pass
