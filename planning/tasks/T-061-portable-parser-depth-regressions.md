---
id: T-061-portable-parser-depth-regressions
title: Make parser depth regressions portable across supported Python versions
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-055-reject-excessively-nested-configuration-inputs
updated_at: "2026-10-04T22:56:06Z"
---

# T-061-portable-parser-depth-regressions Make parser depth regressions portable across supported Python versions

## Description

Correct the T-055 JSON regression fixtures for Python 3.14 under Release
Hardening. The 20,000-level input parses on 3.14, so existing assertions exercise
schema rejection instead of parser-depth normalization. Preserve production
contracts and use real parser failures below existing byte budgets.

Follow-up derived from T-055-reject-excessively-nested-configuration-inputs's verification or discovery.

## Acceptance

- Prove the JSON fixture raises RecursionError in the actual parser on Python
  3.12, 3.13, and 3.14 before testing shared loaders and CLI normalization.
- Preserve exact error messages, structured exit 2, no traceback, no bundle,
  safe YAML, size budgets, and all existing validators without production changes.
- Pass the repository gate and supported Python suites, complete independent
  review, and confirm the automatic remote main Build is green after push.

## Verification Notes

- Clean reconciled base: a5019c7f48cf7ff73679f823a1b838c29a34098c equals origin/main.
- Actual CPython 3.14.7: json.loads parses 20,000 levels (40,001 bytes), but
  raises RecursionError at 100,000 levels (200,001 bytes), below 16 MiB.
- Original `uv run --python 3.14 pytest tests/unit/input_depth_test.py --tb=line -q`:
  4 failed, 6 passed. Exact failures match remote Build 37239114193: model
  contract and validation schema rejection replace parser-boundary diagnostics.

## Implementation Notes

### Workflow-v3 evidence

1. Understand: fetched origin/main and confirmed clean matching base. Follow-up
   created with `taskrail task new --follow-up T-055-reject-excessively-nested-configuration-inputs`
   and started through supported commands; status checked after both writes.
   Release Hardening's stable invalid-input exit and structured diagnostic
   contract governs the work. No runtime/schema/API change is needed.
2. Strict TDD: original 3.14 affected tests: 4 failed, 6 passed. Added a shared
   fixture requiring `json.loads` to raise RecursionError before normalization
   tests; retaining 20,000 levels produced 10 setup errors, each
   `Failed: DID NOT RAISE RecursionError`. Changed only fixture depth to 100,000:
   same `uv run --python 3.14 pytest tests/unit/input_depth_test.py --tb=line -q`
   produced 10 passed. Production stays unchanged; exact messages were not
   relaxed to arbitrary invalid-input rejection.
3. Initial checks: Ruff, formatting, mypy passed. Ran sequentially for each
   version `uv run --python <version> python -c 'import sys; print(sys.version)'`,
   `uv run --python <version> pytest tests/unit/input_depth_test.py --tb=line -q`,
   and `uv run --python <version> pytest -q`. Actual CPython 3.12.14, 3.13.11,
   and 3.14.7 each: 10 affected tests passed, 817 full tests passed.
4. Dedicated Task loaded personal code-simplifier: no edits recommended;
   affected 3.14 tests 10 passed and diff whitespace check passed.
5. Three parallel independent read-only Tasks loaded personal code-reviewer:
   General (common code-reviewer guidance), Python (python-reviewer plus
   python-patterns), Security (security-reviewer plus security-review/common
   security rules). All returned verbatim: "No concrete task-relevant findings."
   General covers acceptance/test quality; Python covers exception/runtime
   compatibility; Security covers input-boundary assertions. Database,
   frameworks and domain lanes omitted: none of those implementations changed.
   Two specialists fit the soft budget. Fresh candidate-validation Task loaded
   code-reviewer and returned "No concrete task-relevant findings." Zero
   candidates, accepted/rejected IDs, or duplicates; it also ran 10 affected
   tests successfully on actual 3.13.11.
6. Dispositions: empty finding set; no fixes, deferrals, or rejected suggestions.
7. Final `mise run setup` installed hooks. `mise run check` exit 0 on 3.13.11:
   Ruff passed, 61 files formatted, strict mypy passed on 60 source files,
   817 tests passed, commit/push-message, author, mutation-floor/differential,
   and orb-setup guard suites passed. `git diff --check` passed. Fresh read-only
   Task loaded code-reviewer disposition-verification and returned verbatim
   "No concrete task-relevant findings." Empty dispositions verified, one
   cycle, no unresolved/new issues. No mutation run: production logic unchanged.
8. Finalize after review: verification/completion use Taskrail commands, with
   git status after each write. Commit uses installed hooks and the configured
   maintainer identity. Authorized fast-forward push and automatic remote Build
   monitoring follow implementation completion; remote results are reported in
   the delivery response, not presumed from local tests. No manual dispatch,
   release, deployment, publishing, tagging, or history rewrite is authorized.

The fixture intentionally asserts parser behavior rather than mocking it or
skipping on Python 3.14. If a future supported runtime increases its parser
limit, the explicit precondition will fail instead of silently testing schemas.
- 2026-10-04T22:56:06Z: verification pass
- 2026-10-04T22:56:06Z: Test-only correction reviewed and locally verified across supported Python versions; push and automatic Build monitoring follow.
