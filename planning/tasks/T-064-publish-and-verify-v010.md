---
id: T-064-publish-and-verify-v010
title: Publish and verify v0.1.0
status: todo
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-063-release-preparation
updated_at: "2026-10-20T19:11:11Z"
---

# T-064-publish-and-verify-v010 Publish and verify v0.1.0

## Description

Execute and verify the external v0.1.0 release after T-063 prepares the candidate.
This tracks publication left unperformed by T-029 under the active spec's
release-hardening scope. Creating this task is not authorization to publish:
obtain explicit maintainer approval for shared publisher/environment setup,
tagging, workflow dispatch, and publication before taking those actions.

## Acceptance

- PyPI and TestPyPI trusted publishers match the workflow and environment
  identities in docs/releasing.md. GitHub pypi and testpypi environments have
  the documented approval and deployment protections; no stored index token
  replaces OIDC trusted publishing.
- The approved candidate passes release checks. Finalize the dated v0.1.0
  changelog and verified release links using the actual publication date;
  package version and tag match, and the tag points at current origin/main.
- The exact release tag is published to TestPyPI through test-index.yml before
  the GitHub release is published. Verify index visibility and clean-install
  CLI/demo behavior, recording the interpreter and distribution identity.
- Publish the GitHub release with reviewed evidence notes, including the
  required live-integration and authorized-dataset disclosures, then verify
  that release.yml publishes the intended distributions to PyPI.
- Verify PyPI visibility, distribution checksums/provenance, and clean-install
  version/help and offline demo behavior. Record release, workflow, and index
  URLs and any remaining limitations without claiming real-world model validity.
- Follow the runbook's immutable-version failure policy: never overwrite or
  reuse an uploaded version, and do not treat deleting a tag as package rollback.

## Verification Notes

- Follow docs/releasing.md and the reviewed release-notes-v0.1.0.md template.
- Record approvals and successful TestPyPI/PyPI workflow URLs, exact tag/commit,
  package metadata/checksums, and clean-environment installation/demo results.
- Recheck origin/main immediately before tagging and publication because both
  workflows require the tag to match current main.
- Record failure or blocked evidence honestly; only mark publication verified
  after the published artifacts and installation are independently checked.

## Implementation Notes
