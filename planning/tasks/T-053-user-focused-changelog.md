---
id: T-053-user-focused-changelog
title: Correct unreleased changelog and focus entries on users
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-26T11:28:04Z"
---

# T-053-user-focused-changelog Correct unreleased changelog and focus entries on users

## Description

Correct the premature v0.1.0 release claim and condense the changelog into
user-facing outcomes, under the active spec's release-hardening requirement.
Guide future agents to preserve accurate release status and concise entries.

## Acceptance

- All initial development remains under Unreleased, with no dated release
  heading or links to the nonexistent v0.1.0 tag.
- Entries describe user capabilities rather than internal implementation and
  verification history, while retaining material evidence limitations.
- AGENTS.md explains user-focused writing and when release headings are valid.
- Release metadata tests no longer require an unpublished version to be dated.

## Verification Notes

- `uv run pytest tests/unit/release_test.py -q`: the corrected assertion failed
  on the old dated heading (1 failed, 4 passed), then passed after the changelog
  correction (5 passed).
- `uv run ruff check`: all checks passed.
- `uv run ruff format --check`: 58 files already formatted.
- `uv run mypy`: no issues found in 58 source files.

## Implementation Notes

- Condensed the initial changelog into six capability bullets and three
  limitations, linking existing technical documentation for detail.
- Removed the premature release heading and tag-based links; linked Unreleased
  to the main tree until an authorized first publication.
- Added changelog writing and publication-evidence guidance. No runtime code,
  publishing workflows, published history, or prior task statuses changed.
- 2026-09-26T11:28:04Z: verification pass
- 2026-09-26T11:28:04Z: Corrected and condensed changelog, added agent writing guidance, and verified release-status regression.
