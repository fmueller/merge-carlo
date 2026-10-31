# Changelog

Notable user-facing changes are recorded here using
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Start from package installation and an offline demo without cloning the
  repository. The PyPI README now links directly to versioned guides and
  examples, separates developer setup, and keeps unverified live-data behavior
  explicit.

### Fixed

- The collection date-window example now uses the supported `--end` option
  with a timezone-aware timestamp.

## [0.1.0] - 2026-10-31

Initial release of the offline-first scenario explorer.

### Added

- Run an offline synthetic demo to explore pull-request review workflows
  without GitHub access or an LLM.
- Compare reproducible scenarios for arrival volume, AI-origin work, reviewer
  schedules, absences, and hypothetical review bypass. Model revision loops,
  verification, and abandonment separately from active review effort.
- Collect GitHub review history read-only with resumable collection, then
  inspect data coverage and missingness before using it. Stored projections
  exclude bodies, patches, tokens, and email addresses; AI origin is never
  inferred from account type.
- Build and calibrate empirical models through the Python API, with explicit
  effort assumptions and parameter provenance. A [local authorized workflow](docs/live-workflow.md)
  documents collection through persisted simulation and reports blocked results
  when evidence is incomplete.
- Run saved models with `simulate`, check held-out evidence with `validate`,
  and generate Markdown reports from saved artifacts with `report`, without
  rerunning simulations. Reports show queueing, review latency, throughput,
  uncertainty, and fit diagnostics; truncated runs disable policy ranking.
- Automate workflows with JSON Lines console output (`--json`), stable exit
  codes, and configuration JSON Schema export (`schema`).

### Fixed

- Held-out validation measures first completed review decisions, not review
  starts; unfinished reviews provide no completion evidence. The elapsed-delay
  benchmark excludes completions at or after the replay end, matching FIFO's
  half-open horizon. Operational review-start latency is unchanged.
- Persisted simulation accepts valid calibrations with no descriptive review
  or merge observations while keeping active-effort inputs strictly validated.
- Invalid duration kinds, excessively nested inputs, and unrepresentable
  simulation dates return exit 2, including structured diagnostics under
  `--json`, without replacing an existing simulation bundle. Representable
  boundary dates no longer fail on unused calendar iteration dates.

### Limitations

- **Live GitHub integration has not been run.** No authorized dataset was
  collected, so live collection, real-team calibration, and real-data
  validation remain unverified. Demo results are synthetic, not measured team
  behavior.
- Scenario comparisons do not establish productivity gains, defect or security
  risk, or the safety of review bypass. See [model limitations](docs/limitations.md)
  for interpretation guidance and unsupported workflows.
- [Performance measurements](docs/performance.md) cover one synthetic workload
  on one machine, not a general runtime or scalability guarantee.

[Unreleased]: https://github.com/fmueller/merge-carlo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fmueller/merge-carlo/releases/tag/v0.1.0
