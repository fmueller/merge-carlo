---
id: T-001-repository-bootstrap
title: Bootstrap the repository toolchain, CI, and commit policy
status: in_progress
priority: high
spec_ref: specs/v0.1.0.md#goals
dependencies: []
updated_at: "2026-09-09T19:05:35Z"
---

# T-001-repository-bootstrap Bootstrap the repository toolchain, CI, and commit policy

## Description

Set up the repository so tracked work can start: packaging and a pinned
toolchain, lint, type, and test configuration, continuous integration, the
commit message and authorship policy, the contributor and agent documents, and
the v0.1.0 spec with its milestone backlog. No simulation behavior is
implemented here.

## Acceptance

- `uv sync --locked --dev` installs the project from a committed lockfile.
- `uv run merge-carlo --version` prints the package version.
- Lint, formatting, type checks, and tests pass locally and in CI on Python 3.12, 3.13, and 3.14.
- The `commit-msg` and `pre-push` hooks reject attribution trailers, agent session links, and agent author identities; their suites also run in CI.
- `taskrail validate` reports a valid state and every task resolves to a live spec heading.

## Verification Notes

- Run `mise run check`.
- Run `taskrail validate` and `taskrail coverage`.
- Confirm the `Build` workflow is green on the default branch.

## Implementation Notes
