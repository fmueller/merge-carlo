---
id: T-066-pre-release-dependency-updates
title: Integrate pending dependency updates before first PyPI release
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-063-release-preparation
updated_at: "2026-10-31T09:55:34Z"
---

# T-066-pre-release-dependency-updates Integrate pending dependency updates before first PyPI release

## Description

Rebase and merge the pending Dependabot action updates before the next release,
as requested by the maintainer. Keep publisher actions pinned to verified
upstream commits and preserve the existing release identity and approval gates.

## Acceptance

- PRs #24 (setup-python) and #25 (PyPI publishing action) are updated against
  current main, with their diffs inspected and action pins checked upstream.
- Each updated head passes required checks before merge; any failure is
  diagnosed rather than bypassed. Combined main passes the full local gate.
- No publishing workflow is dispatched or package published by this task.

## Verification Notes

- Inspect exact PR-head CI, upstream release-tag commits, merged diffs, and
  final combined-main checks. Run mise run check and taskrail validate.

## Implementation Notes

- Rebased PR24 to 0211c4d6439ad850c6e48072823cd8424b664648 and PR25 to
  8fe696e80aaeb344097c4ef85e7549c376bc6199. Each had all eight checks pass
  before squash merge. Both are merged; no open PR remains at this checkpoint.
- Upstream setup-python v7.1.0 resolves to
  6d4fd22b20465ccc0f7354476588e8df7c9ca0e0; publisher v1.14.3 peels to
  7245906fb61fa33a13554f9d5fb856fe61758086. Release pinning, OIDC,
  environments, attestations and checksum/artifact boundaries are unchanged.
- Independent code-review found no concrete compatibility/security issue.
  Inspection of PR25's rebased diff confirmed only its two publisher pins.
- Combined main f8d71ab4761579f2808fc41d805e8fdebf870cd2 passed mise run
  check: 817 tests, Ruff/format, strict mypy and all guard suites.
- An initial linked-worktree hook exposed a Git fixture isolation bug and
  created an accidental fixture commit. Removed only that accidental commit,
  restored local repository configuration, and reran corrected-head CI before
  merge. An optional follow-up was offered; no fixture code was changed here.
- No release/publishing workflow was dispatched by this dependency task.
- 2026-10-31T09:55:34Z: verification pass
