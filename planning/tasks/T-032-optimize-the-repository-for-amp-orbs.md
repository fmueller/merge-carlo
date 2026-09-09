---
id: T-032-optimize-the-repository-for-amp-orbs
title: Optimize the repository for Amp orbs
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-09T21:15:44Z"
---

# T-032-optimize-the-repository-for-amp-orbs Optimize the repository for Amp orbs

## Description

Prepare fresh Amp orbs with the repository's pinned developer tools, locked
Python dependencies, and commit hooks before an agent starts work. Keep wake-up
handling empty and fast because this repository has no long-lived services or
authentication repair work.

## Acceptance

- `.agents/setup` bootstraps mise when the orb image does not provide it, then
  installs the locked toolchain and Python development environment without an
  interactive prompt.
- Taskrail is part of the pinned developer toolchain so agents can follow the
  repository's tracked-work lifecycle on a fresh orb.
- Setup is idempotent, completes in under two minutes on cold and warm runs,
  and `.agents/resume` completes in seconds without reinstalling dependencies.
- Both lifecycle scripts are executable, syntactically valid Bash, and covered
  by the local check task.
- `.amp/portals/*` is ignored for future supervised-service portal metadata.

## Verification Notes

- Cold setup completed in 5.44 seconds, warm setup in 0.67 seconds, and resume
  in 0.00 seconds.
- A clean minimal login shell resolved mise 2026.9.3, uv 0.9.17, lefthook
  2.1.10, and Taskrail v0.4.0 from the pinned environment.
- Forged and non-executable mise recovery tests proved setup never falls back
  to an unverified executable. A shell-metacharacter checkout path proved the
  persisted profile fragment does not evaluate path contents.
- `mise run check`, `taskrail validate`, and `git diff --check` passed. Commit
  history fixtures isolate their hook path so user-global hooks cannot alter
  their test messages.

## Implementation Notes

- mise is bootstrapped from pinned Linux x64/arm64 archives and both the
  archive and extracted executable are verified before atomic installation.
- Network stages have bounded deadlines below Amp's setup timeout.
- 2026-09-09T21:11:03Z: implemented and independently reviewed
- 2026-09-09T21:11:11Z: verification pass
- 2026-09-09T21:15:44Z: verification pass
