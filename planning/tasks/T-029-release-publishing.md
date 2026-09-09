---
id: T-029-release-publishing
title: Publish the v0.1.0 release from a trusted workflow
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-027-performance-benchmark
    - T-028-release-documentation
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
