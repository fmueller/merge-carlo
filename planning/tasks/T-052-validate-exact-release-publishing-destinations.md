---
id: T-052-validate-exact-release-publishing-destinations
title: Validate exact release publishing destinations
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-19T11:25:40Z"
---

# T-052-validate-exact-release-publishing-destinations Validate exact release publishing destinations

## Description

Address CodeQL alert #1 (`py/incomplete-url-substring-sanitization`) in the
release workflow test, within the release-hardening spec boundary. Validate
the parsed publishing action rather than searching the whole YAML text.

## Acceptance

- TestPyPI publishing requires exactly `https://test.pypi.org/legacy/`.
- Production PyPI publishing must not override `repository-url`.
- Reject lookalike hosts, path-only matches, unrelated destinations, missing
  TestPyPI configuration, and production destination overrides.
- Preserve the actual publishing workflows and application behavior.

## Verification Notes

- In-memory deliberate workflow mutations produced expected AssertionError
  failures for lookalike hosts, path-only matches, unrelated destinations,
  and production overrides; a missing TestPyPI URL produced KeyError.
  Restoring the real workflow loader passed the same test.
- `uv run pytest -q tests/unit/release_test.py`: 5 passed.
- `uv run ruff check`: all checks passed.
- `mise run check`: 691 tests passed; Ruff, format, strict mypy (58 source
  files), and all commit/push/author/mutation-floor/orb-setup guards passed.
- Dedicated code-simplifier review: no changes needed; focused tests passed.
- Independent code-reviewer General, Security, and Python lanes, followed by
  fresh candidate validation and disposition verification, each concluded:
  "No concrete task-relevant findings." No findings deferred; one review cycle.
- Database and framework lanes omitted because no related behavior changed.
- GitHub alert status cannot be read with the integration's permissions;
  server-side CodeQL resolution remains unconfirmed pending a new scan.

## Implementation Notes

- Replace the loose whole-file substring assertion with exact parsed action
  input checks. This is test hardening only; no runtime or release configuration
  changes, so no user-visible changelog or documentation update is needed.
- 2026-09-19T11:25:40Z: verification pass
