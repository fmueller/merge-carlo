---
id: T-008-abandonment
title: Resolve abandonment as an exogenous competing event
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-007-revision-loops
updated_at: "2026-09-10T14:36:22Z"
---

# T-008-abandonment Resolve abandonment as an exogenous competing event

## Description

Model abandonment as an exogenous competing event: a declared deadline
probability and a positive elapsed-time distribution sampled at pull request
entry. Reaching the deadline cancels future work and releases review occupancy,
counting only the service actually consumed. A deadline after a merge has no
effect, and a deadline at or before a candidate completion wins over that
completion.

## Acceptance

- Abandonment during active review counts only consumed service, releases the reviewer, and prevents any later completion from merging the pull request.
- A deadline later than an achieved merge changes nothing.
- A deadline coinciding with a merge time resolves to abandonment, deterministically.
- Closed-without-merge outcomes remain in reporting rather than being dropped as unexplained.

## Verification Notes

- Deterministic fixtures for each ordering of deadline and completion.
- A conservation test that abandoned work still balances the ledger.

## Implementation Notes

- Implemented entry-time `Abandonment` assumptions: probability and equally
  weighted finite positive elapsed-second samples, with stable proposal-purpose
  keys. Deadlines precede completions; horizon censoring retains precedence at
  the half-open boundary. Cancellation releases active or paused reviewers and
  skips stale loop events; closed outcomes remain in boundaries and summaries.
- Workflow-v3: understood spec/state/accounting contracts; initial ordering
  tests failed three missing-API cases, then passed with minimal scheduling.
  Removing the pending terminal guard deliberately produced four transition
  errors; restoration passed all five cancellation fixtures.
- Initial full gate: 255 tests passed, Ruff/format/mypy and shell guards passed.
  Dedicated code-simplifier consolidated reviewer loops and hoisted imports;
  accepted after diff inspection and focused tests. No architecture changes.
- Independent General and Python code-reviewer lanes loaded their ECC reviewers;
  Python also loaded python-patterns. Both concluded: "No concrete task-relevant
  findings." Fresh candidate validation confirmed the empty finding set.
  Security, database, framework and UI lanes were omitted because no such
  boundaries changed. No review findings were rejected or deferred.
- Raw differential mutation inspection exposed two multi-proposal test gaps.
  Added asymmetric abandonment/surviving-review and abandonment/surviving-CI
  fixtures. Deliberately replacing both terminal-skip `continue` statements with
  `break` failed both cases (duplicate boundary; missed merge). Restoring correct
  code passed both. A fresh disposition-verification reviewer confirmed both
  resolved and reported: "No concrete task-relevant findings."
- Final `mise run check`: 257 passed; Ruff, formatting, mypy (19 files), commit,
  push, author, mutation-floor and orb-setup guard suites passed. Final scoped
  `BASE=93e71d3ef0a09251cced553277eb8ccccad3af8d mise run test:mutate`:
  engine 464/475 (97.7%), using the unchanged 80% floor. Raw counts: 461 killed,
  3 timeouts (counted by policy), 11 survived; no suppression or floor override.
  Surviving run_fifo mutant numbers: 11/19/25/29/51 diagnostic wording;
  81 zero-duty endpoint; 88/121/259 horizon-only inert event registration;
  132/134 initial previous time overwritten before use. Raw results are retained
  in local manual-test evidence, located by the Taskrail verification report.
- Manual direct Python API exercise, independent of pytest helpers, passed
  active cancellation/release, post-merge deadline, exact completion tie and
  closed-outcome conservation. Plan/report are ignored local evidence;
  the verification report records their location. Temporary directory removed.
  No CLI simulation
  artifact contract is claimed by this Python primitive.
- One review/disposition/recheck cycle completed. No new follow-up task was
  needed. Existing T-033 remains explicitly applicable before the v0.1.0 release
  mutation gate: decorated dataclass methods, including parameter validation,
  are not represented by the mutation score. No second task was implemented.
- 2026-09-10T14:36:22Z: verification pass
