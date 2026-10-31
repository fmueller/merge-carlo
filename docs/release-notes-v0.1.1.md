# merge-carlo v0.1.1

This patch is the first PyPI release, published on 2026-10-31. v0.1.0 was published on
GitHub and TestPyPI; its PyPI publication was cancelled before upload.

## What changed

- The README starts with package installation and a checkout-free offline
  demo, links to versioned documentation and examples, and separates advanced
  calibration and contributor setup.
- The collection date-window example uses `--end` with a timezone-aware
  timestamp. Simulator behavior is unchanged.
- Publishing workflows use the reviewed setup-python and PyPI publisher
  updates merged before this candidate.

## Evidence and limitations

- **Live GitHub integration has not been run.** No authorized dataset was
  collected for this release. Live collection, real-team calibration, and
  real-data validation remain unverified.
- The demo is synthetic. Conditional simulation comparisons do not establish
  causal productivity gains, defect or security risk, or review-bypass safety.
- Mutation testing runs asynchronously each week, not as a release gate.
  Historical mutation results do not establish real-world model validity.
- Performance measurements cover one synthetic workload on one machine, not
  a general runtime or scalability guarantee.

T-067 records candidate checks, TestPyPI rehearsal and post-upload PyPI
installation verification separately. Both publication workflows succeeded,
index files matched their workflow artifacts, and clean PyPI installation,
version/help and the offline demo passed. The actual package-page README and
logo were inspected at wide and narrow widths. These checks establish package
delivery, not real-data model validity.

See the [changelog](https://github.com/fmueller/merge-carlo/blob/v0.1.1/CHANGELOG.md),
[implementation evidence](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/implementation-status.md),
and [model limitations](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/limitations.md).
