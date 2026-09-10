---
id: T-007-revision-loops
title: Simulate verification and requested-change revision loops
status: completed
priority: high
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-005-keyed-random-streams
updated_at: "2026-09-10T13:43:01Z"
---

# T-007-revision-loops Simulate verification and requested-change revision loops

## Description

Simulate the verification gate and the requested-change loop: an aggregate
elapsed verification delay with no runner-capacity queue, a failure leading to
an author response and a new revision, and separate first-visit and repeat
requested-change probabilities. Enforce the engine safety limit on visits and
attempts.

## Acceptance

- A run where all first reviews request changes and later reviews approve produces exactly two review visits per non-abandoned pull request.
- Verification failing once then passing produces a new revision, and no human review begins before the passing gate.
- First-visit and repeat requested-change probabilities are separately configurable and separately applied.
- Exceeding the visit or attempt limit marks the replication `engine_truncated`; it never forces a merge or masquerades as abandonment.
- A truncated replication is excluded from outcome summaries, its count is shown, and the comparison is marked incomplete.

## Verification Notes

- Deterministic mechanics fixtures with probabilities pinned to zero or one.
- A test asserting that a truncated replication disables policy ranking.

## Implementation Notes

### Workflow-v3 evidence

1. Understand: started from origin/main at
   `54f70faa4243ba3e4bb284fe1f4379b79ea108ae`; Taskrail validation passed and
   deterministic next selected this task. Lifecycle transitions already owned
   revision invalidation. Extended only the FIFO engine and its tests; preserved
   fresh inputs, stable ordering, self-review exclusion, exact internal time,
   half-open censoring and assumed (not observed) delay/probability provenance.
2. TDD: `uv run pytest tests/unit/simulation/engine_test.py -q` initially
   failed collection because `RevisionLoops` did not exist, then passed 24
   tests after minimal implementation. Added horizon, validation, concurrent
   verification and Hypothesis loop-invariant coverage. An overstrict property
   asserting unique public float timestamps was corrected: distinct exact
   internal event times can round to the same public float.
3. Initial checks: ruff and strict mypy passed; full pytest passed 218 tests.
4. Dedicated Task loaded personal `code-simplifier`: no edits recommended;
   exact scheduling and separate cumulative/visit service were already minimal.
   Its focused check passed 54 tests, ruff and mypy.
5. Separate parallel General and Python review Tasks loaded `code-reviewer`.
   General loaded ECC code-reviewer; Python loaded ECC python-reviewer and
   python-patterns. No security, database, framework, or ML lanes: no affected
   trust boundary, persistence, framework, or learned-model behavior. Each
   returned verbatim: "No concrete task-relevant findings." Fresh candidate
   validation confirmed the empty set; no rejected or deduplicated candidates.
6. No reviewer findings to fix or defer. Mutation inspection independently
   exposed missing exact-threshold/default-seed coverage. Strengthened tests
   killed `x_run_fifo__mutmut_1`, `_2`, `_182`, `_261` (default identity and
   `<` changed to `<=` in both Bernoulli decisions); restored behavior passed
   56 focused tests. Summary coverage includes nonzero unresolved counts and
   exclusion of earlier merges within a truncated diagnostic.
7. Final checks: `mise run check` passed (ruff, format, strict mypy, 220 pytest
   tests, commit/push/author/mutation/orb-setup guard suites). Taskrail validate
   and `git diff --check` passed. Fresh disposition verification returned
   "DISPOSITION VERIFICATION: PASS" and "No concrete task-relevant findings."
   It ran 188 simulation/domain/randomness tests plus ruff/mypy/diff checks.
   One review cycle; no unresolved findings. Its direct Taskrail invocation
   lacked PATH activation; the implementer reran `mise exec -- taskrail validate`
   successfully before finalization.
8. `taskrail verify` passed and `taskrail complete` completed this task only,
   after all review gates. The generated local verification report is ignored
   by repository policy; these committed notes retain its evidence and result.
   Taskrail reports 11 done, 26 todo, no active/blocked/off-spec work; exact next
   task is T-009-ai-arrival-transforms. Shipping is explicitly authorized.

### Mutation evidence and limitations

`BASE=54f70faa4243ba3e4bb284fe1f4379b79ea108ae mise run test:mutate`
passed the unchanged 80% scoped gate for `merge_carlo.simulation.engine`:
395/405 detected (97.5%). Raw statuses: 391 killed, 4 timeout, 10 survived,
0 suspicious, 0 untested. The gate includes timeouts as detections, not kills.

All surviving IDs are in `x_run_fifo`: `_11`, `_19`, `_25`, `_29`, `_51`
change diagnostic wording without changing its tested meaning; `_81` adds a
zero-length clipped interval; `_88` and `_120` enqueue horizon work that the
horizon-first branch never executes; `_131` and `_133` change the unused
initial previous timestamp before any assignment exists. No equivalent
mutants were suppressed. Timeouts `_126`, `_165`, `_293`, `_318` alter event
progress/shift/service accounting. Raw results were inspected with
`uv run mutmut results --all true` and `uv run mutmut show <id>`.

Decorated dataclass validators/properties remain absent from mutmut discovery;
the score does not establish their efficacy. Existing v0.1.0 follow-up
T-033-dataclass-mutation-coverage owns this limitation; no mutation workaround
or policy change was added here.

### Manual verification and downstream work

An independent synthetic Python API fixture used two proposals, one reviewer,
3-second visits, 2-second verification and 5-second author response. Both had
two visits and merged at 15 and 18 seconds. Combining that run with a
verification-truncated run yielded completed=1, truncated=1, merged=2,
unresolved=0, incomplete=true and policy_ranking_enabled=false. No UI changed.

Filed T-037-comparison-truncation-reporting through Taskrail, explicitly
required for v0.1.0: carry the implemented Python truncation gate into future
persisted comparison artifacts/reports after T-014, including cross-scenario
and assumption-set propagation. It was not implemented here. Constant assumed
delays and the Python-only API scope are documented in docs/limitations.md.
- 2026-09-10T13:43:01Z: verification pass
