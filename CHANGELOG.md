# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Read-only GitHub transport Python API with same-origin pagination and
  redirects, bounded requests and payloads, conditional requests, rate-limit
  handling, explicit collection status and credential-safe diagnostics.
- One-command offline synthetic demo with reproducible example inputs, the
  scenario suite, model/results artifacts and a report that labels every major
  section synthetic and states that only the base assumption set was run.
- Versioned experiment artifact bundles and artifact-only deterministic Markdown
  reports through the Python API, with run-level summaries, paired merge deltas,
  Wilson uncertainty intervals, escaped exports and staged publication.
- Measurement-window metric dictionaries for operational and new-ready work,
  with queue integrals, completed-review latency quantiles, mature-cohort shares,
  clipped utilization, explicit undefined reasons, and run-level summaries.
- Sequential paired Monte Carlo execution across named assumption sets, with
  streamed rows, continuous warm-up, separate count summaries, truncation
  gating, and opt-in sampled engine diagnostics through the Python API.
- Repository setup: packaging, pinned toolchain, lint, type, and test
  configuration, continuous integration, commit policy hooks, and the v0.1.0
  spec with its milestone backlog.
- A command-line entry point exposing `--version` and `--help`.
- Typed, immutable pull-request lifecycle contracts with guarded transitions,
  revision invalidation, terminal outcomes, and review accounting.
- Timezone-aware duty calendar primitives with weekly windows, dated absences,
  explicit DST boundary rejection, and local-day horizon and warm-up bounds.
- A deterministic FIFO review engine with constant active service, stable
  reviewer selection, no self-review, shift pause/resume, horizon censoring,
  conservation boundaries, and separate active/duty accounting.
- Verification and requested-change revision loops with keyed decisions,
  separate first/repeat change probabilities, elapsed author-response delays,
  and inclusive safety limits. Truncated runs are excluded from pooled outcome
  counts and disable the comparison's policy-ranking gate.
- Exogenous abandonment deadlines sampled at proposal entry from assumed
  probability and positive elapsed-duration samples. Deadlines win completion
  ties, cancel future work, release reviewers, and retain consumed service;
  closed-without-merge outcomes remain in conservation and pooled counts.
- Stateless purpose-keyed NumPy PCG64 random streams, reproducible by root
  seed, replication, and ordered proposal/revision/purpose keys.
- Whole-week arrival resampling with bundled author/origin marks, stable
  proposal identities, timezone mapping, and an `exploratory_only` flag for
  fewer than eight complete training weeks.
- Typed additive and replacement AI arrival overrides, stable shared proposals
  across load sweeps, and realized cohort counts on proposal schedules.
- Named review-calendar replacements and reviewer-specific half-open absences,
  with explicit-offset boundaries and immutable FIFO-ready capacity resolution.
- Hypothetical review bypass with assumed eligibility or operator labels,
  independently keyed audits, verification-gated bypass and elapsed merge
  coordination. Qualified whole-run diagnostics report unreviewed merges and
  assumed review demand avoided, with unsupported risk and safety fields null.
- Project marks in `assets/`: a fan logo for the README and social preview,
  a die favicon and avatar for small sizes, both adapting to light and dark.
- Amp orb lifecycle scripts that prepare the pinned toolchain and locked
  development dependencies on fresh remote machines.

### Changed

- Scope differential mutation verdicts to changed modules, rejecting missing
  selected execution without counting unrelated cached results. Full-gate
  per-module checks and raw mutation counts remain unchanged.
- Lower the default per-module mutation efficacy floor from 90% to 80% for
  v0.1.0 by explicit maintainer decision. Raw mutation results, survivors,
  per-module accounting, and the ten-mutant minimum remain unchanged.

[Unreleased]: https://github.com/fmueller/merge-carlo/compare/main...HEAD
