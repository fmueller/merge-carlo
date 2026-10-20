---
id: T-063-release-preparation
title: Finalize v0.1.0 release preparation
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-029-release-publishing
updated_at: "2026-10-20T19:23:34Z"
---

# T-063-release-preparation Finalize v0.1.0 release preparation

## Description

Prepare a coherent, verified v0.1.0 release candidate under the active spec's
release-hardening scope. T-028 and T-029 delivered documentation and publishing
infrastructure, not an actual publication. Refresh their evidence without
rewriting completed task history or claiming that a release already exists.

## Acceptance

- README clearly presents the purpose, supported workflow, first successful
  offline run, installation versus contributor setup, and modeling limitations.
  Published-package instructions are explicitly pending publication verification.
- CHANGELOG.md presents a consolidated, user-facing initial-release summary,
  including relevant fixes and interpretation limits, without implementation
  logs. All pending changes remain under Unreleased; no release date, tag
  comparison, or publication claim is invented.
- Release notes, implementation status, and release instructions agree on the
  current candidate, remaining external setup, and unverified authorized live
  collection, real-team calibration, and real-data validation.
- Stale mutation-discovery and remaining-work statements are reconciled against
  current evidence. Machine-managed task fields and STATE.md are changed only
  through supported Taskrail commands; unresolved lifecycle limits are recorded.
- The full local gate, distribution build, metadata checks, and documented
  offline demo pass, with objective evidence recorded for the candidate.
- No tag, GitHub release, package upload, or shared publisher/environment
  configuration is created or changed by this preparation task.

## Verification Notes

- Run taskrail validate and inspect the generated state and dependencies.
- Run mise run check, uv build, and uv run twine check on the distributions.
- Exercise the documented offline demo in a disposable directory and inspect
  its artifacts and limitations; remove scratch outputs afterward.
- Review README, changelog, release notes, and runbook together for consistent
  installation, evidence, publication order, and unsupported-model claims.

## Implementation Notes

2026-10-20 preparation based on origin/main at
`a03a2761972f0e4b6532b367945d802fea3455c7`. Documentation and tracked state only;
no executable source, dependency, publishing workflow, or shared configuration
changed. No commit, push, tag, release, workflow dispatch, or upload performed.

Workflow evidence:

1. Read acceptance, active release-hardening scope, README/changelog, release
   runbook/notes, evidence ledger, mutation policy/limitations, and task history.
   T-029 is infrastructure only; real-data evidence and publication are unverified.
2. No executable behavior changed, so no red/green production-code test was
   introduced. Existing documentation/pipeline contracts were retained; manual
   source/metadata/demo probes validate the prose rather than asserting wording.
3. Initial `mise run check` passed: 817 tests plus lint, format, strict types and
   all five guard suites. Documentation/release contracts passed: 11 tests.
4. Dedicated personal-skills:code-simplifier Task simplified three documentation
   files only; its 11 contract tests and diff whitespace check passed. Changes
   were inspected and accepted.
5. Independent code-reviewer General-lane Task inspected actual diff/contracts:
   "No concrete task-relevant findings." General alone covers this prose/state
   scope; Python, framework, security and database lanes omitted because no
   corresponding implementation or boundary changed. A fresh candidate-validation
   Task confirmed no findings and `taskrail validate` passed.
6. No findings to fix or defer. No historical task outcome was rewritten.
7. Final `mise run check` passed: Ruff, format, mypy (60 files), 817 pytest tests
   in 15.53 seconds and all guard suites. Distribution/demo checks below passed.
   Fresh code-reviewer disposition verification returned "No concrete
   task-relevant findings." One review cycle; no unresolved findings.
8. Taskrail verification/completion is recorded through the CLI after review.

Distribution and offline evidence (disposable `/tmp/merge-carlo-t063` outputs,
removed after inspection; not saved release distributions):

- `uv build --out-dir <scratch>/final-dist` built wheel and sdist for 0.1.0;
  `uv run twine check <scratch>/final-dist/*` reported PASSED for both.
- Wheel metadata: name/version, Python >=3.12,<3.15, LICENSE and console entry
  point matched pyproject; sdist includes README and LICENSE.
- `uv run --offline --no-sync merge-carlo demo --out <scratch>/demo --seed 42
  --replications 200` succeeded on Python 3.13.11. All nine artifacts present;
  six baseline/scenario groups each requested/usable 200, zero engine truncations,
  synthetic=true, validation_status=not_performed, base assumptions only, all
  three unsupported safety fields null in report, traces empty. Eight manifest
  content hashes verified. Repeated demo: `diff -qr` exit 0, byte-identical files.
- In-memory discovery with locked mutmut 3.8.0: calendars 293 mutants, including
  DutyCalendar.materialize 135; domain 367, including PullRequest.transition 151;
  relevant @property methods 0. No mutant execution, efficacy or runtime claim.
- `taskrail unblock T-033-dataclass-mutation-coverage --reason ...` removed the
  obsolete 3.7.0 release-availability blocker through the supported lifecycle.
  T-033 remains todo under v0.2.0; T-036 reopening completed work remains open.
- Read-only CI inspection: starting commit Build run 39481536857 passed; latest
  Mutation tests run 39194092474 passed at a376de153d002627c8b6a33205d412e9f9a6eadb,
  not the local preparation candidate. No fresh full mutation gate claimed.

Remaining: review/land preparation, separately authorize T-064, confirm trusted
publishers/protected environments, tag reviewed main, rehearse TestPyPI, publish
GitHub release/PyPI, verify index distributions and clean installation/demo.
No authorized live dataset or verified real-team calibration/real-data validation.
- 2026-10-20T19:23:34Z: verification pass
