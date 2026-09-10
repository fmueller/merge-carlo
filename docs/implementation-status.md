# Implementation status

What is built, what was verified, and what remains unverified. Update this file
in the same commit as the change it describes.

Last updated: 2026-09-10.

## Milestones

| Milestone | Scope | Status |
| --- | --- | --- |
| M0 | Repository setup: packaging, toolchain, CI, commit policy, spec and backlog | Complete |
| M1 | Deterministic core: domain contracts, calendars, one queue, constant service | In progress: domain contracts and calendars |
| M2 | Stochastic scenario slice: keyed randomness, arrival transforms, loops, bypass | In progress: keyed random streams and week-template arrivals |
| M3 | Experiment and report: replication runner, paired deltas, metrics, offline demo | Complete: Python artifacts and one-command synthetic demo |
| M4 | Read-only data pipeline: GitHub adapter, projected store, provenance, quality report | In progress: transport, store and cohort collection |
| M5 | Empirical model and validation: week templates, features, held-out diagnostics, benchmark | Not started |
| M6 | Release hardening: schemas, docs, benchmark, optional authorized live smoke test | Not started |

## Verified

- `collect --resume` reconciles all-state/open PRs and paginated reviews and
  lifecycle events into the projected store. Synthetic fixtures cover old open
  PRs, closed-without-merge outcomes, duplicate conflicts, half-open bounds,
  partial children, interruption and resume identity checks. Later snapshots
  are excluded from historical cutoffs. See [collection](cohort-collection.md).
- `merge-carlo demo --out out/demo --seed 42 --replications 200` runs the
  synthetic scenario suite with only the base assumption set. Integration tests
  forbid HTTP-client/socket construction and compare repeated artifacts byte for
  byte. Every report section labels synthetic evidence and incomplete sensitivity.
  Example week records, assumptions, and overrides are embedded in the resolved
  experiment artifact; no real-data extraction or calibration is implied.
- `artifacts.write_experiment` publishes versioned experiment bundles with
  streamed paired rows and sampled diagnostics. `reporting.render_report` reads
  saved summary artifacts only. Tests cover paired merge deltas, run-level
  summaries, Wilson intervals, escaping, deterministic report text and failed
  publication rollback. See [artifact API](artifacts.md); CLI wiring is pending.
- The sequential Python replication runner pairs each scenario with its baseline
  under the same assumption and replication keys. Tests cover continuous warm-up,
  reproducibility, scenario ordering/addition, capacity/demand/bypass forwarding,
  truncation exclusion, separate assumption summaries, opt-in sampled diagnostics,
  and live memory independent of replication count. Measurement metrics and
  persisted experiment/report artifacts are now available through Python; see
  [runner limitations](limitations.md#uncertainty).
- `simulation.arrivals.generate_proposals` resamples caller-certified complete
  local weeks with replacement, retaining readiness/author/origin bundles.
  Tests cover stable proposal IDs and latent keys, timezone week boundaries,
  DST mapping/rejection, half-open clipping, and the `exploratory_only` label
  below eight distinct training weeks (including empty weeks). Results contain
  fresh FIFO-compatible proposals with readiness seconds from the UTC span's
  start; dataset extraction and stochastic engine integration remain pending.
  Scoped mutation testing exceeds the v0.1.0 80% floor; decorated dataclass
  validators remain outside mutmut discovery (existing T-033).
- Purpose-keyed streams pass call-order, consumption-isolation, key-boundary,
  numeric canonicalization, and cross-process hash-seed checks. Use
  `simulation.randomness.random_stream(42, 0, "pr-17", 1, "effort")` to get a
  fresh NumPy `Generator(PCG64(SeedSequence(...)))`. Root seed and replication
  are non-negative integers; ordered key components are strings or integers,
  with integers converted to decimal strings. The identity is a compact ASCII
  JSON array of strings, hashed with SHA-256 and interpreted as one big-endian
  integer for SeedSequence. Repeating the call restarts the sequence; retain
  the generator for successive draws. Common latent keys must omit scenario
  identifiers, letting scenarios transform the same draws. This is a Python
  primitive only; stochastic engine integration remains
  tracked work. See [limitations](limitations.md#random-streams).
- Duty calendars pass spring-forward and fall-back UTC fixtures, absence
  subtraction and conservation tests, overnight clipping, and local-day run
  bound checks. See [calendar semantics](calendars.md) for boundary rules and
  the Python API; scheduler integration is still pending.
- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, and
  `uv run pytest` pass on the package skeleton.
- `uv run merge-carlo --version` prints the package version.
- The commit policy guard suites pass: `scripts/check-commit-msg-test.sh`,
  `scripts/check-push-messages-test.sh`, `scripts/check-author-test.sh`. The
  negative cases were exercised directly: an agent session trailer, a
  co-authorship line, and an agent author identity are each rejected.
- Mutation testing is wired: `mise run test:mutate` (differential),
  `mise run test:mutate:gate` (full), and a weekly workflow. On the CLI skeleton
  the gate reports `merge_carlo.cli` at 2/3 killed, below the ten-mutant minimum,
  so it is labeled insufficient evidence rather than given a verdict. The one
  survivor is an equivalent mutant: `typer.Exit(code=0)` and
  `typer.Exit(code=None)` both exit zero, so no test can distinguish them.
- The `Build` workflow is green on `main`: lint and type checks, the commit
  policy guards, and the test suite on Python 3.12, 3.13, and 3.14.

## Not implemented

The real-data pipeline commands — `inspect`, `calibrate`, `validate`,
`simulate`, and `report` — remain unimplemented. The CLI exposes `collect`, `demo`,
`--version` and `--help`. The README distinguishes working and planned commands.

## Unverified

- **Live GitHub integration has never been run.** No authorized dataset has been
  collected, and no real-data validation has been performed. Nothing in this
  repository should be read as a claim that live collection was tested.
- No performance benchmark has been recorded.
