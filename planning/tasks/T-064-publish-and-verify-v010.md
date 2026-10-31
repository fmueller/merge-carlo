---
id: T-064-publish-and-verify-v010
title: Publish and verify v0.1.0
status: blocked
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-063-release-preparation
updated_at: "2026-10-31T09:48:29Z"
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

Release authorized by the maintainer on 2026-10-31 after registration of both
trusted publishers. GitHub environments were inspected read-only: both require
fmueller approval; pypi allows v* tags, testpypi allows main and v* tags.

Pre-publication evidence:

- `mise run setup` installed hooks and synchronized the locked environment.
- `mise run check` passed: 817 tests, Ruff/format, strict mypy (60 files), and
  all five guard suites. Focused documentation/release checks passed 11 tests.
- The specifically pre-release changelog assertion was transitioned to the
  authorized dated-release contract: red before the changelog update, green
  afterward. No production code or publishing workflow changed.
- Dedicated simplifier made no changes. The low-risk conventional-review
  coordinator and independent General code-review lane found no concrete
  findings; coordinator reconciliation approved the finalization diff.
- `uv build` produced wheel and sdist; `uv run twine check` passed for both.
  Wheel version, Python bounds, and console entry point were checked. A clean
  Python 3.13.11 wheel installation passed version/help and the seed-42,
  200-replication offline demo. Demo manifest hashes and synthetic/unvalidated
  evidence flags were checked.
- Finalization commit: 60eaf6e5482991f30cfc3b7ffcce922389d258b9. Annotated
  v0.1.0 tag and origin/main both resolve to that commit. Do not advance main
  during rehearsal/publication because the workflows enforce this identity.
- Build https://github.com/fmueller/merge-carlo/actions/runs/41189201111
  passed, including Python 3.12/3.13/3.14. CodeQL run 41189200987 passed.
- Fresh full mutation gate dispatched for this exact commit:
  https://github.com/fmueller/merge-carlo/actions/runs/41189216129 . Still
  running at the TestPyPI checkpoint; no fresh mutation pass is claimed yet.

TestPyPI checkpoint:

- Maintainer approved the environment job; the trusted-publishing upload passed:
  https://github.com/fmueller/merge-carlo/actions/runs/41189333111 .
- Index https://test.pypi.org/project/merge-carlo/0.1.0/ exposes wheel and sdist.
  Both index SHA-256 values match the downloaded workflow distributions and
  their SHA256SUMS manifest:
  wheel 3d34fdeafbd62c83587ffcae3ceff8035f1f53a73eadd695d977ee07be090882;
  sdist f4f7db6302f30c935d866ce0964a3f11bdbc0518b08006f89f0efbf759c1fbbf.
- Upload logs confirm generation/upload of digital attestations for both files.
- An isolated Python 3.13.11 environment installed the exact TestPyPI wheel
  URL with its SHA-256 fragment, resolving dependencies exclusively from PyPI.
  Version/help passed, and the seed-42, 200-replication demo succeeded. All
  eight manifest content hashes and synthetic/validation-not-performed flags
  passed inspection. Runtime dependencies included Pydantic 2.14.2 and NumPy
  2.5.4; this is installation evidence, not real-data model validation.

Pending: published GitHub release, maintainer
PyPI environment approval, PyPI upload and independent artifact/provenance and
clean-install checks. T-064 remains in progress. No GitHub release or PyPI
publication is claimed at this checkpoint. Scratch evidence is under
`/tmp/merge-carlo-v010-release` in the release thread's orb until final checks.

Maintainer decision on 2026-10-31: full mutation testing is asynchronous weekly
assurance, not a release gate. Do not wait for or require a fresh mutation run
for publication. The existing dispatched run may finish independently; its
outcome does not replace Build, TestPyPI rehearsal, or clean-install checks.
Runbook and release notes updated accordingly without changing the weekly
workflow, efficacy policy, published tag, or frozen release commit. These
documentation/evidence changes will land after publication so main remains at
the release tag throughout the publisher identity checks.
- 2026-10-31T09:48:29Z: Superseded by maintainer decision: preserve v0.1.0 tag/TestPyPI artifacts, cancel PyPI upload, improve README and publish v0.1.1 first after merging pending Dependabot updates.
