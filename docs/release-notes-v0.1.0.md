# merge-carlo v0.1.0

This release delivers the offline-first v0.1.0 simulator, its versioned
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

See [`CHANGELOG.md`](../CHANGELOG.md) and
[`docs/limitations.md`](limitations.md) for the complete release notes and
limitations.
