---
id: T-067-first-pypi-v011
title: Prepare v0.1.1 as the first PyPI release with package-facing documentation review
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-066-pre-release-dependency-updates
updated_at: "2026-10-31T10:38:38Z"
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

### TestPyPI rehearsal verified — 2026-10-31

This checkpoint supersedes the pending TestPyPI statements above; production
PyPI publication and verification remain pending.

- Candidate commit: b1932d21520b7547956a5255220dd75684d4d5f3, tagged v0.1.1.
  Build 41192526412 and CodeQL 41192526371 passed. TestPyPI workflow
  https://github.com/fmueller/merge-carlo/actions/runs/41192649167 succeeded
  after maintainer approval. Main and the release tag were not advanced during
  rehearsal verification.
- https://test.pypi.org/project/merge-carlo/0.1.1/ exposes both distributions.
  Downloaded index files match the workflow artifacts and index digests:
  wheel SHA-256 a713b16976747570978c9d435254e087eacc274efadc65d61a9202b3010b0946;
  sdist SHA-256 e65641df58c396a18bc85265257828cc4d06a47fcb0d2cb3aa503a1d81d3d5f3.
  Published metadata has Python >=3.12,<3.15, Apache-2.0 and Markdown description;
  the description exactly matches the tagged README.
- A clean Python 3.13 environment installed the exact TestPyPI wheel URL, with
  dependencies resolved from PyPI. A mixed-index first-index attempt could not
  resolve NumPy because TestPyPI carries an older version; using an explicit
  TestPyPI wheel URL avoids that ambiguity without relaxing resolver security.
  Installed --version reports 0.1.1, --help succeeds, and the seed-42 offline
  demo completes six groups with 200 usable replications each, zero truncation,
  and all eight manifest hashes verified. Results remain synthetic/unvalidated.
- Actual TestPyPI page inspected in Chromium at wide and narrow widths. Logo
  loads through TestPyPI's image proxy at 44 px beside the title; badges,
  installation and direct demo commands render correctly with no page overflow.
  All 15 versioned documentation/example destinations exist in the remote
  tagged tree. Wheel provenance metadata names the expected GitHub repository,
  test-index.yml workflow and testpypi environment, with the matching wheel
  digest; this metadata inspection is not an independent signature verification.
- Screenshots and read-only recordings are under
  .amp/in/artifacts/testpypi-v011/. Keep this checkpoint uncommitted until the
  publication stage permits advancing main; no GitHub release or PyPI upload
  was started by this rehearsal.

### PyPI publication verified — 2026-10-31

This checkpoint supersedes the pending-publication statements above.

- Maintainer authorized the GitHub release and separately approved the pypi
  environment. https://github.com/fmueller/merge-carlo/releases/tag/v0.1.1 was
  published at 2026-10-31T10:31:18Z. Workflow
  https://github.com/fmueller/merge-carlo/actions/runs/41193085574 succeeded.
  Published tag still identifies b1932d21520b7547956a5255220dd75684d4d5f3;
  no tag, distribution or prior release was rewritten.
- https://pypi.org/project/merge-carlo/0.1.1/ exposes the wheel and sdist.
  Downloaded files match PyPI digests and the production workflow artifacts:
  wheel SHA-256 5111426b64731158f75babf5775c969f2c5772efe177f3ca89b70b90d7faf207;
  sdist SHA-256 9249f14e75de76bcd72293dae65d18dd13e61632c00e7eec520bbb02989a152c.
  Published version and README exactly match the tagged source. Production
  hashes need not equal the separately built TestPyPI archives; each index was
  checked against its own workflow artifacts.
- A fresh Python 3.13 environment installed merge-carlo==0.1.1 from PyPI.
  --version reports 0.1.1 and --help succeeds. The documented uv tool install
  command also succeeded using isolated tool/bin directories and the PyPI index.
  The installed seed-42, 200-replication demo passed: six groups, 200 usable
  each, no engine truncation, all eight manifest hashes verified. Synthetic and
  not_performed validation labels remain intact.
- Actual production PyPI description inspected at wide and narrow widths.
  Logo loads at 44 px through the image proxy; badges, installation and direct
  demo instructions are readable without page overflow or broken images.
  Inspected screenshots: .amp/in/artifacts/pypi-v011/. The browser recording
  failed with an encoder-lag error; screenshots and DOM checks were preserved.
- PyPI provenance metadata identifies release.yml, fmueller/merge-carlo and
  the pypi environment and binds the matching wheel digest. This is metadata
  inspection, not independent cryptographic signature verification.
- Finalization records the actual publication date and evidence after upload;
  it changes documentation/task state only, not the immutable published package.
  Authorized live integration, real-team calibration and real-data validation
  remain unverified. Weekly mutation testing was not dispatched or awaited.
- 2026-10-31T10:38:38Z: Published v0.1.1 to PyPI after TestPyPI rehearsal and maintainer approvals; verified distribution identity, clean installations, offline demo, actual package-page logo and docs; final evidence reviewed.
- 2026-10-31T10:38:38Z: verification pass
