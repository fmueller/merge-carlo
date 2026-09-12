---
id: T-029-release-publishing
title: Publish the v0.1.0 release from a trusted workflow
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-027-performance-benchmark
    - T-028-release-documentation
    - T-030-mutation-floor-gate
    - T-037-comparison-truncation-reporting
    - T-039-experiment-cli
    - T-040-artifact-validator-mutations
    - T-041-cli-command-mutations
    - T-043-host-independent-mutation-kills
updated_at: "2026-09-09T19:03:12Z"
---

# T-029-release-publishing Publish the v0.1.0 release from a trusted workflow

## Description

Publish v0.1.0: add the release workflows using trusted publishing, cut the
changelog entry, and tag the release. Publishing happens only when separately
requested.

## Acceptance

- A release workflow builds and publishes on a published release, with a separate manually dispatched test-index workflow.
- Publishing uses trusted publishing rather than a stored token.
- `CHANGELOG.md` has a dated `0.1.0` section and the version matches `pyproject.toml`.
- The release notes state the evidence status, including whether live integration was verified.

## Verification Notes

- A dry-run build with `uv build` and a metadata check with `twine check`.
- Confirm the test-index publish succeeds before the real one.

## Implementation Notes

Release ordering (maintainer decision, 2026-09-11): release tasks come after
every other open v0.1.0 task, so this task depends on all of them. By later
maintainer decision the same day, T-033 (dataclass mutation discovery, blocked
on a PyPI mutmut release containing boxed/mutmut#539), T-020 (optional CI
enrichment), and T-036 (Taskrail reopening support) moved to v0.2.0 and no
longer gate this task or T-030.
