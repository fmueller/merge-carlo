---
id: T-018-cohort-collection
title: Collect and reconcile the pull request cohort
status: completed
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-017-projected-store
updated_at: "2026-09-10T18:59:59Z"
---

# T-018-cohort-collection Collect and reconcile the pull request cohort

## Description

Collect and reconcile the historical cohort: enumerate pull requests in all
states plus all currently open ones, union by immutable identifier, include both
pull requests created inside the analysis interval and older ones open during
it, fetch child collections completely, and deduplicate because the repository
changes while extraction runs. Store the analysis interval, retrieval time, and
source event or snapshot time separately.

## Acceptance

- Old inactive open pull requests are captured even though an update-time cutoff would omit them.
- Closed-without-merge and still-open pull requests are retained, so arrivals are not biased toward fast completions.
- Every collection carries `complete`, `partial`, `unavailable`, or `not_requested`; a safety limit yields `partial`, never a falsely complete dataset.
- `collect --resume` resumes through a reconciliation pass rather than a saved page offset, and an interrupted run leaves either partial data marked incomplete or the previous complete artifact.
- A later snapshot is stored with its observation time and never used as if known earlier.

## Verification Notes

- Fixture tests with changed page order, duplicate rows, old open pull requests, and a partially interrupted extraction.
- A test that a future snapshot attribute cannot leak into a historical feature cutoff.

## Implementation Notes

Implemented the read-only collector and `collect --resume` CLI. Requested
collections are PRs, reviews and issue lifecycle events; optional CI and derived
features are explicitly not_requested. Readiness/origin inference remains T-019.
Snapshot observation time is distinct from retrieval completion and event time;
historical access conservatively excludes later and undated snapshots.

### Workflow evidence

| Step | Evidence | Result |
| --- | --- | --- |
| 1 Understand | Taskrail validate/next selected T-018 at origin/main 21b1a40; inspected ingestion spec, transport, projected store, CLI and tests. | Scope: unbiased cohort retention, partial-result semantics, atomic resume, privacy and temporal boundaries. |
| 2 Strict TDD | Initial cohort test failed with missing module; first CLI test failed with missing collect command. Fractional timestamps, malformed events and unsafe identity diagnostics produced five focused failures before fixes. | Initial cohort/transport/store suite 99 passed; expanded suite 508 passed. |
| 3 Initial checks | Ruff, formatter, mypy and full pytest; focused cohort/store/github/CLI checks. | 508 full tests, 122 focused tests passed before review. |
| 4 Simplify | Dedicated Task loaded code-simplifier; removed redundant post-projection TypeAdapters, retained validation through Manifest and projection. Parent inspected changes and reran focused tests. | 122 passed; Ruff and mypy passed; no rejected behavioral changes. |
| 5 Review | Four separate parallel read-only Tasks loaded code-reviewer: General, Python, Security, Database. Fresh candidate-validation Task validated SEC-001. | One validated finding; no duplicate or rejected candidates. |
| 6 Disposition | SEC-001 fixed with four failing CLI retry cases: identity 403, malformed metadata, invalid repo and KeyboardInterrupt left dataset.sqlite. Cleanup now removes only a new empty database after SQLite closes. | Four red cases became green; CLI suite 10 passed. No deferred findings. |
| 7 Recheck | Fresh code-reviewer disposition-verification Task loaded Security guidance and verified cleanup/preservation; full mise run check and manual CLI pass. | RESOLVED; no concrete task-relevant findings. One review/fix cycle. |
| 8 Finalize | Taskrail verify and complete only after review and final checks; authorized direct-main commit/push follows final validation. | See generated verification report and repository history. |

Lane guidance loaded: General ECC code-reviewer and common rules; Python ECC
python-reviewer plus python-patterns; Security ECC security-reviewer plus
security-review/common security; Database ECC database-reviewer plus
postgres-patterns and database-migrations (applied only where relevant to SQLite).
All loaded reviewer-index routing. General is mandatory; the three specialist
lanes cover Python, external input/privacy and persistence, within the default
budget. No web-framework, frontend, ML or network-configuration lane was relevant.
General, Python and Database each concluded: "No concrete task-relevant findings."

### Validated review finding (verbatim)

FINDING SEC-001 — errors
Severity: medium
Evidence: `src/merge_carlo/cli.py:83-97` creates the workspace, output directory,
and `dataset.sqlite` before calling `collect_cohort`; repository validation and
identity retrieval occur only at `src/merge_carlo/cohort.py:73-78`, while the
initial resumable partial manifest is not written until
`src/merge_carlo/cohort.py:90-106`.
Finding: A validation or repository-identity failure can leave a nonempty dataset
with no extraction manifest, making the output unusable by either a normal retry
or `--resume`.
Failure/impact: For an invalid repository or an identity request returning
401/403/malformed data, the command exits after SQLite initialization. A normal
retry rejects the nonempty output at `cli.py:78-79`; `--resume` opens it but fails
because `store.manifests()` is empty. Users must manually diagnose and delete
application-created state, violating safe nonempty-output/resume behavior.
Recommended direction: Validate the repository and fetch its immutable identity
before creating dataset state, or remove a newly created database when failure
occurs before the initial manifest is committed. Add a CLI test that retries
after identity failure and confirms either the output remains absent/empty or
`--resume` succeeds safely.

Disposition: fixed. Fresh verifier: "RESOLVED — Disposition verified." and
"No concrete task-relevant findings." Its independent CLI check: 10 passed.

### Final verification and mutation limits

- `mise run check`: passed; Ruff, format, strict mypy (40 files), 512 pytest
  tests, commit-message/push-message/author/mutation-floor/orb-setup guard suites.
- `git diff --check`: passed.
- Manual `collect --help` and real CLI/MockTransport/SQLite harness in a temporary
  directory passed: old open/unmerged PRs retained; page limit exits 3; interrupted
  resume exits 130 with unchanged hash; successful reconciliation leaves one
  extraction/two PRs/two reviews; historical snapshots/future events excluded;
  identity-failure retry works. Temporary helper and data removed.
- Manual plan/report:
  `planning/artifacts/manual-test/T-018-cohort-collection/20260910T185342Z/`.
- `BASE=origin/main mise run test:mutate` executed the four changed modules,
  twice (before and after disposition). Both wrapper invocations exited 1 due
  to existing T-038: Unicode-mangled class-method names are dropped by its
  parser, reporting GitHub results missing. This is not a passing wrapper run.
- Raw `uv run mutmut results --all true` accounting below includes those methods.
  Passing the identical records through `sed 's/ǁ/__/g'` into the scoped floor
  checker changes only name separators, not module ownership, status or counts.
  That scoped 80% check passed. No production/tooling changes, exclusions or
  lowered floor were used to obtain the result.

| Module | Killed | Timeout | Survived | Total | Policy efficacy |
| --- | ---: | ---: | ---: | ---: | --- |
| cohort | 255 | 0 | 40 | 295 | 86.4%, pass |
| github | 441 | 9 | 87 | 537 | 83.8%, pass (timeouts counted by existing policy) |
| store | 364 | 0 | 76 | 440 | 82.7%, pass |
| cli | 2 | 0 | 1 | 3 | Insufficient evidence, below 10-mutant minimum |

No selected mutants remain unexecuted. CLI decorated commands are not discovered
by the pinned mutmut (existing T-041); its equivalent version-exit survivor is
not suppressed. The score does not establish mutation coverage of collect.
Existing T-038 and T-041 remain explicitly v0.1.0 release-hardening work; no
duplicate follow-up task was filed and no second task was implemented.

Remaining limitations: fixture-only live integration; collection is not a
point-in-time GitHub transaction; do not run concurrent collectors against one
dataset. Raw observed fields are not calibrated historical features. Exact next
product task: T-019-readiness-and-origin (use medium mode per orchestration).
- 2026-09-10T18:59:33Z: verification pass
