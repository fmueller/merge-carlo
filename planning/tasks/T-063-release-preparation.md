---
id: T-063-release-preparation
title: Finalize v0.1.0 release preparation
status: todo
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-029-release-publishing
updated_at: "2026-10-20T19:11:04Z"
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
