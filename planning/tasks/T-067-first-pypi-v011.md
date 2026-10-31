---
id: T-067-first-pypi-v011
title: Prepare v0.1.1 as the first PyPI release with package-facing documentation review
status: in_progress
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-066-pre-release-dependency-updates
updated_at: "2026-10-31T09:55:34Z"
---

# T-067-first-pypi-v011 Prepare v0.1.1 as the first PyPI release with package-facing documentation review

## Description

Prepare and publish v0.1.1 as the first PyPI release after the maintainer's
README review and dependency-update decision. Preserve the published v0.1.0
GitHub tag/release and immutable TestPyPI files; its PyPI upload is cancelled.
This remains a release-hardening patch, not new simulator behavior or a claim
of real-data model validity.

## Acceptance

- README leads with package installation, installed-CLI demo usage and a clear
  output description; contributor setup and advanced calibration are linked.
- Images and documentation links work outside GitHub. Internal release queue
  details are removed, the unsupported --until example is corrected, and
  synthetic/model-validity/live-integration limitations remain explicit.
- Repository agent guidance requires a package-facing README/docs review for
  future release sessions, including rendered output, links/images, install
  and first-run commands, status accuracy, and preserved evidence limitations.
- Package version, lockfile, changelog, release notes and workflow defaults
  consistently target 0.1.1. No published tag or distribution is rewritten.
- Full local checks, build/metadata checks, independent review and rendered
  package-description inspection pass. Weekly mutation testing remains
  asynchronous assurance, not a release gate.
- Following authorized tagging and TestPyPI rehearsal, clean installation,
  distribution identity and synthetic demo are verified before PyPI approval.
  PyPI upload and clean-install verification complete before task completion.

## Verification Notes

- Run mise run check, build wheel/sdist, check metadata and package README,
  inspect rendered description and absolute resource targets, then verify the
  actual TestPyPI page and a clean installed-CLI demo.
- Record exact release/tag commit, reviewed checks, both index workflow URLs,
  distribution hashes/provenance and clean-install results. Retain approval
  boundaries and do not advance main between tagging and publication.

## Implementation Notes

- README now leads with `uv tool install merge-carlo==0.1.1` and a direct
  installed-CLI demo; advanced calibration lives in its owning guide. Resource
  URLs are absolute and version-pinned. The header logo uses an absolute raw
  URL pinned to an existing commit with identical SVG content. Transient
  publisher-setup prose was removed without weakening model limitations.
- Corrected both the unsupported date option and its cohort semantics: the end
  excludes later PR creations, not retained PRs' child history. Extended the
  existing cohort test with after-end review/lifecycle evidence; temporary
  in-memory wrong-cutoff probes fail for each kind, while the real code passes.
- Package metadata, lockfile root version, TestPyPI default and new release
  notes target 0.1.1. Dependency resolution, simulator source and historical
  v0.1.0 tag/distributions are unchanged. Changes remain under Unreleased.
- AGENTS.md and the release runbook require independent package-facing
  README/docs analysis, rendered inspection, usable resource links and clean
  installation/first-run evidence. Weekly mutation testing is explicitly
  asynchronous and non-gating.
- Focused docs checks first failed on relative resources and the old duplicated
  calibration presentation, then passed. Full local gate passed 818 tests,
  Ruff, formatting, strict mypy (60 source files) and all five policy guards.
  The simplifier made no changes. Independent general, docs, release-integrity
  and status-claims reviews ran; the docs review found the cohort wording above.
- Local wheel and sdist builds passed Twine. Isolated installations report
  0.1.1; the wheel's offline seed-42, 200-replication demo completed all six
  baseline/scenario groups with 200 usable each and no engine truncation.
  All eight manifest hashes match; output remains synthetic and unvalidated.
- The packaged description was rendered using readme-renderer 46.0 with its
  Markdown extra, then inspected in Chromium at wide and narrow widths.
  Badges load and the page has no horizontal overflow. All 15 versioned
  resource paths exist locally. Remote v0.1.1 URLs require the future tag;
  local rendering is not an actual TestPyPI/PyPI page verification.
- Publication-stage work remains: reviewed candidate delivery, tag creation,
  TestPyPI rehearsal and rendered-page/install checks, maintainer approvals,
  PyPI upload and post-upload verification. No 0.1.1 index upload or index
  installation is claimed. Keep this task in progress until those succeed.
