---
id: T-029-release-publishing
title: Publish the v0.1.0 release from a trusted workflow
status: completed
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
updated_at: "2026-09-14T02:21:26Z"
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

### Workflow-v3 evidence

1. Understand: the v0.1.0 release contract requires separate trusted PyPI and
   manually dispatched TestPyPI workflows, versioned release notes, and no
   stored publishing token. The workflow validates the release tag, package
   version, current `origin/main` commit, release evidence, and stable-release
   status before dependency installation or package build.
2. Strict TDD: the new release contract tests initially failed because the
   dated changelog section and workflows were absent. The focused suite then
   passed (`2 passed`). Security/order tests were red against the initial
   workflow, and passed after the gates moved before dependency setup. A
   deliberate `needs: broken-build` regression failed (`1 failed, 1 passed`),
   and a deliberate wrong publisher path failed (`1 failed, 3 passed`); both
   were restored and the final focused suite passed (`4 passed`).
3. Checks: `mise run check` passed with 685 tests, Ruff, format, strict mypy,
   commit/push/author/mutation/orb guard suites. `uv build` and
   `uv run twine check dist/*` passed. YAML parsing and actionlint v1.7.12
   passed. `BASE=origin/main mise run test:mutate` correctly found no changed
   source modules.
4. Simplify: the dedicated `code-simplifier` pass made no changes; separate
   workflows were retained because merging them would obscure their distinct
   triggers and trusted-publisher identities.
5. Independent review: General and Security `code-reviewer` lanes, candidate
   validation, and disposition verification were completed. The review covered
   OIDC permissions, environment trust, action pinning, tag/version invariants,
   artifact checksums and provenance, release-note injection, failure/rollback
   behavior, test coverage, and scope.
6. Disposition: validated findings G-001, SEC-001, and SEC-002 were fixed. The
   final verifier found all three resolved and no new task-relevant finding.
7. Final review: the final diff is ready for Taskrail verification. No release
   tag, GitHub release, TestPyPI upload, or PyPI upload was performed.

### Implementation and external publication state

- `.github/workflows/release.yml` builds from a published release tag, checks
  `twine` metadata, transfers the exact distributions with a checksum manifest,
  and publishes with job-scoped OIDC trusted publishing and PyPI attestations.
- `.github/workflows/test-index.yml` provides the separate manual TestPyPI
  rehearsal using the same tag/version/source checks and artifact boundary.
- `docs/releasing.md` records the exact trusted-publisher identities,
  protected-environment requirements, publication order, and irreversible
  PyPI failure behavior. `docs/release-notes-v0.1.0.md` and the dated changelog
  section explicitly state that live GitHub integration was not run.
- Remote inspection found no `v0.1.0` tag or GitHub release, and both PyPI and
  TestPyPI returned 404 for `merge-carlo`. GitHub environment/protection API
  inspection was unavailable to the current token. Actual publication therefore
  remains blocked until the two index projects/publishers and protected
  environments are configured and the TestPyPI rehearsal succeeds; it must not
  be replaced with a stored token.
- 2026-09-14T02:21:18Z: verification pass
