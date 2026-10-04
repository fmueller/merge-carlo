# Changelog

Notable user-facing changes are recorded here using
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Initial v0.1.0 development; no release has been published.

- Added a local workflow for authorized GitHub repository testing, including
  token-safe collection, calibration, persisted simulation, and explicit
  blocked results for incomplete evidence.
- Fixed persisted simulation for valid calibrations with no descriptive review
  or merge observations while keeping active-effort inputs strictly validated.
- Excessively nested configuration and JSON artifact inputs now return invalid-input
  errors (exit 2), including structured diagnostics under `--json`, rather than tracebacks.
- Simulation dates outside the supported datetime range now return invalid-input
  errors (exit 2), including under `--json`, without replacing an existing bundle.
  Nearby representable runs no longer fail on unused calendar iteration dates.

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
  effort assumptions and parameter provenance.
- Run saved models with `simulate`, check held-out evidence with `validate`,
  and generate Markdown reports from saved artifacts with `report`, without
  rerunning simulations. Reports show queueing, review latency, throughput,
  uncertainty, and fit diagnostics; truncated runs disable policy ranking.
- Automate workflows with JSON Lines console output (`--json`), stable exit
  codes, and configuration JSON Schema export (`schema`).

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

[Unreleased]: https://github.com/fmueller/merge-carlo/tree/main
