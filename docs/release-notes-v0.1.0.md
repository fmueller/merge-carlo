# merge-carlo v0.1.0

This initial release includes the offline-first v0.1.0 simulator, its versioned
configuration and experiment artifacts, the fixture-backed read-only GitHub
collection path, and the documented release evidence.

## Evidence status

- **Live GitHub integration has not been run.** No authorized dataset was
  collected for this release, so live collection, real-team calibration, and
  real-data validation remain unverified.
- The offline demo, fixture-backed collection behavior, strict checks, type
  checks, and lint were verified in the locked reference environment. Mutation
  testing runs asynchronously each week, not as a release gate. Historical
  mutation results cover discovered functions, not real-world model validity;
  no fresh mutation pass is claimed for this release.
- The performance record covers one synthetic workload on one machine and does
  not make a universal runtime, memory, or scalability claim.

See the [implementation status](https://github.com/fmueller/merge-carlo/blob/v0.1.0/docs/implementation-status.md)
and [mutation policy](https://github.com/fmueller/merge-carlo/blob/v0.1.0/docs/mutation-policy.md)
for the recorded verification and discovery limitations. T-064 records the
publication and clean-install verification separately from model evidence.

See the [changelog](https://github.com/fmueller/merge-carlo/blob/v0.1.0/CHANGELOG.md)
and [limitations](https://github.com/fmueller/merge-carlo/blob/v0.1.0/docs/limitations.md) for the complete release notes and
limitations.
