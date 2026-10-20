# merge-carlo v0.1.0

Draft release notes for the unpublished v0.1.0 candidate. T-029 delivered
publishing infrastructure, not a published package. T-063 prepares the candidate;
T-064 owns the separately authorized publication and post-upload verification.
All pending changelog entries remain under Unreleased until an authorized release.

The candidate includes the offline-first v0.1.0 simulator, its versioned
configuration and experiment artifacts, the fixture-backed read-only GitHub
collection path, and the documented release evidence.

## Evidence status

- **Live GitHub integration has not been run.** No authorized dataset was
  collected for this release, so live collection, real-team calibration, and
  real-data validation remain unverified.
- The offline demo, fixture-backed collection behavior, strict checks, type
  checks, lint, and release mutation gate were verified in the locked reference
  environment. The mutation gate is test-efficacy evidence for discovered
  functions, not evidence of real-world model validity.
- The performance record covers one synthetic workload on one machine and does
  not make a universal runtime, memory, or scalability claim.

The current local check, build, metadata, and offline demo evidence is recorded
in [implementation status](implementation-status.md). Historical mutation runs
are identified separately in the [mutation policy](mutation-policy.md); they
are not a fresh full mutation run for this documentation-only preparation.
Trusted publishers and protected environments require maintainer confirmation;
the TestPyPI rehearsal, PyPI upload, and published-package installation remain
unverified. Follow [the release runbook](releasing.md) only with separate
authorization for those external actions.

See [`CHANGELOG.md`](../CHANGELOG.md) and
[`docs/limitations.md`](limitations.md) for the complete release notes and
limitations.
