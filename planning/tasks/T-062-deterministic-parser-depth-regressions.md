---
id: T-062-deterministic-parser-depth-regressions
title: Use a deterministic real JSON parser for depth normalization regressions
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-061-portable-parser-depth-regressions
updated_at: "2026-10-04T23:11:43Z"
---

# T-062-deterministic-parser-depth-regressions Use a deterministic real JSON parser for depth normalization regressions

## Description

Automatic Build 37241977510 exposed a compiler/build-dependent C JSON scanner
limit: GitHub CPython 3.14.7 accepts the 100,000-level T-061 fixture, whereas
the orb's CPython 3.14.7 rejects it. Release Hardening requires portable
regressions proving actual parser-depth failure normalization, not a fixed
universal depth limit. Use the real stdlib Python scanner in these tests only.

Follow-up derived from T-061-portable-parser-depth-regressions's verification or discovery.

## Acceptance

- Real parser raises RecursionError on bounded nested JSON before shared-loader
  and CLI assertions run. Do not fabricate the exception or weaken messages.
- Preserve structured exit 2, no traceback/no bundle, safe YAML and all existing
  validators. No production changes; monkeypatches restored after each case.
- Supported Python affected/full suites and repository gate pass after review.
  Push fast-forward and monitor the automatic remote Build until settled.

## Verification Notes

- Build 37241977510 at 078f6d38142b98ad31e0efaddb8209f623417276: lint, guards,
  Python 3.12/3.13 succeed; actual Python 3.14.7 reports 807 passed, 10 errors
  with `DID NOT RAISE RecursionError` at the new parser precondition.
- Attempt to run the downloaded actions/python-versions Ubuntu 24.04 interpreter
  locally could not execute: orb glibc lacks GLIBC_2.38. No system library or
  project setup changes made. Remote failure is direct evidence on that build.
- Strict red: 2,000-level input with the unchanged C scanner on actual orb 3.14:
  `uv run --python 3.14 pytest tests/unit/input_depth_test.py --tb=line -q`
  reports 10 setup errors, `DID NOT RAISE RecursionError`. Selecting the real
  stdlib Python scanner with an explicit decoder: 10 passed, same command.
- Proved regression detection: temporarily removed RecursionError normalization
  from both JSON loader catches, ran same command: 6 failed, 4 passed (two
  unnormalized RecursionErrors, four CLI exit 1 instead of 2). Restored both
  catches unchanged: 10 passed. Final production diff is empty.

## Implementation Notes

The fixture selects stdlib `scanner.py_make_scanner` and forces a fresh
JSONDecoder through `partial(json.loads, cls=json.JSONDecoder)`, bypassing the
cached C scanner without changing its parsing API or inventing exceptions.
The actual parser consumes 2,000-level JSON (4,001 bytes) and raises the genuine
RecursionError; the precondition guards against schema rejection. Test-scoped
monkeypatch cleanup restores both globals. A narrow attr-defined suppression
documents the scanner entry omitted by Typeshed; no runtime fallback or skip.

### Workflow-v3 evidence

1. Understand: inspected failed automatic Build and exact version; created and
   started this spec-anchored follow-up through Taskrail, checking git status
   after each write. No production or CI configuration change is required.
2. Strict TDD and deliberate normalization regression: red/green commands and
   decisive outcomes are recorded above. No altered source catches remain.
3. Initial Ruff, formatting and mypy pass. Actual CPython 3.12.14, 3.13.11 and
   3.14.7 each passed `uv run --python <version> pytest tests/unit/input_depth_test.py --tb=line -q`
   (10 passed) and `uv run --python <version> pytest -q` (817 passed), after
   selecting the real Python scanner. No unverified interpreter substitution.
4. Dedicated Task loaded personal code-simplifier, no edits recommended;
   actual 3.14 affected tests 10 passed. No suggestions rejected.
5. Parallel independent read-only Tasks loaded personal code-reviewer:
   General (common code-reviewer checklist), Python (python-reviewer and
   python-patterns), Security (security-reviewer and security-review/common
   security rules). Every lane returned verbatim:
   "No concrete task-relevant findings." General covers acceptance/test
   quality, Python covers real parser behavior and pytest isolation, Security
   covers trust-boundary assertions. Two specialists within the soft budget;
   no database/framework/domain implementation changed, so those lanes omitted.
   Fresh candidate-validation Task loaded code-reviewer and returned verbatim
   "No concrete task-relevant findings." Zero candidates/accepted/rejected IDs
   and duplicates. All reviews inspected the actual diff and relevant sources.
6. Empty findings and dispositions; no fixes or deferrals. The negative control
   above proves the strengthened tests fail when normalization regresses.
7. Final `mise run check` exit 0 on actual 3.13.11: Ruff passed, 61 files
   formatted, strict mypy passed on 60 source files, 817 tests passed; commit
   message, push message, author, differential/mutation-floor and orb-setup
   guard suites passed. Fresh read-only Task loaded code-reviewer in
   disposition-verification mode and confirmed no unresolved/new issues,
   returning "No concrete task-relevant findings." One cycle for this
   follow-up. No production mutation run needed beyond the negative control.
8. Supported Taskrail verification and completion follow review. T-061's remote
   failure was recorded through `taskrail verify --result fail`; this follow-up
   supersedes its fixed-depth attempt without rewriting history. Commit/push
   retain installed hooks and maintainer identity; automatic remote Build is
   monitored after push and its actual result returned in the delivery report.

Limitation: this regression deliberately exercises the stdlib Python scanner,
not a universal C scanner depth threshold. All production input validators and
default parser choices remain unchanged and are covered by the full suites.
- 2026-10-04T23:11:43Z: verification pass
- 2026-10-04T23:11:43Z: Reviewed portable real-parser regression correction; authorized push and automatic remote Build monitoring follow.
