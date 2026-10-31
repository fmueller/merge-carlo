# Implementation status

This is the v0.1 scope evidence ledger: what is implemented, what was verified, what
is limited or unsupported, and what remains. “Implemented” does not imply that a
model is validated for a real workflow or that the release is ready to publish.

Last updated: 2026-10-31 (T-067 preparation for the first PyPI release, v0.1.1).

## Milestones

| Milestone | Scope | Status |
| --- | --- | --- |
| M0 | Packaging, pinned toolchain, CI, commit policy, spec and backlog | Complete |
| M1 | Domain contracts, duty calendars and deterministic FIFO engine | Complete |
| M2 | Keyed randomness, revisions, abandonment, demand/capacity scenarios and bypass | Complete |
| M3 | Replication runner, metrics, artifacts, report and synthetic demo | Complete; persisted simulate/report CLI added |
| M4 | Read-only transport/store, cohort collection, attribution and inspection | Implemented; optional CI enrichment deferred to v0.2.0 |
| M5 | Frozen features, provenance-tagged calibration and descriptive validation/benchmark | Complete through Python APIs and offline validation CLI |
| M6 | Schemas, release evidence, performance benchmark, weekly mutation checks and publishing | Implemented; v0.1.0 GitHub/TestPyPI release exists, v0.1.1 PyPI publication pending |

## Implemented command surface

`merge-carlo` exposes `schema`, `demo`, `collect`, `inspect`, `validate`,
`simulate`, and `report`, plus
`--help`, `--version`, and global `--json` console output. Every implemented
command has option help. Human errors are concise and machine mode emits one
JSON object per operational result or error with `status`, `exit_code`, and
`message`; help remains human-readable.

Stable process exit codes are:

- `0`: success, including an exploratory validation report with warnings;
- `2`: invalid or inaccessible input/output;
- `3`: source/access failure or explicitly incomplete collection; and
- `4`: a failed validation gate when `validate --strict` was requested.

## Verification evidence

The v0.1.0 [TestPyPI rehearsal](https://github.com/fmueller/merge-carlo/actions/runs/41189333111)
published wheel and sdist, followed by clean-install and offline-demo verification
recorded in T-064. Its [GitHub release](https://github.com/fmueller/merge-carlo/releases/tag/v0.1.0)
exists, but the [PyPI workflow](https://github.com/fmueller/merge-carlo/actions/runs/41189661905)
was cancelled before upload. T-067 prepares v0.1.1 with a package-facing README;
its index installation and publication remain pending. T-066 merged both
Dependabot updates after passing Build and CodeQL checks.

The checks below are historical T-063 evidence, not a v0.1.1 verification claim.
T-063 checks the local documentation/state candidate based on
[`a03a276`](https://github.com/fmueller/merge-carlo/commit/a03a2761972f0e4b6532b367945d802fea3455c7).
No executable source, dependency, or publishing-workflow change is included.
These local checks do not establish publication or real-world model validity:

| Command | Result | Evidence covered |
| --- | --- | --- |
| `uv run ruff check` and `uv run ruff format --check` | Pass | Lint and formatting |
| `uv run mypy` | Pass: 60 files | Strict type checking |
| `uv run pytest` (within `mise run check`) | Pass: 817 | Full automated suite, including documented pipeline and offline demo contracts |
| `mise run check` | Pass | CI-equivalent lint, format, types, tests and five guard suites |
| `uv build --out-dir "$dist_dir"` | Pass: wheel and sdist for `0.1.0` | Local distribution build in disposable output |
| `uv run twine check "$dist_dir"/*` | Pass: both distributions | Distribution metadata and README rendering contract |
| `uv run --offline --no-sync merge-carlo demo --out "$demo_dir" --seed 42 --replications 200` | Pass | Six scenario/baseline groups, 200 usable each, no engine truncations; synthetic, validation not performed, base assumptions only |
| `mise exec -- taskrail validate` | Pass | Task structure, references and generated state |

`dist_dir` and `demo_dir` are fresh disposable paths, not saved release assets.
The demo produced all nine documented artifacts, including empty opt-in traces;
unsupported safety fields remain null. All eight manifest content hashes were
verified, and a second run with the same inputs produced byte-identical files
(`diff -qr` exit 0). Wheel metadata matched the name, version, Python bounds,
license and CLI entry point; the sdist included README and LICENSE. This is
local synthetic evidence only, not an index installation check.

The starting commit's [Build run](https://github.com/fmueller/merge-carlo/actions/runs/39481536857)
passed. The latest inspected [Mutation tests run](https://github.com/fmueller/merge-carlo/actions/runs/39194092474)
passed at
[`a376de1`](https://github.com/fmueller/merge-carlo/commit/a376de153d002627c8b6a33205d412e9f9a6eadb),
not at this documentation candidate. No new full mutation run is claimed by
T-063; historical scores below must not be substituted for current discovery.

The historical full mutation check (T-030) was run separately on 2026-09-11:
`mise run test:mutate:gate` passed with every one of 22 modules at or above the
80% floor, including `merge_carlo.simulation.engine` 601/613 (98.0%),
`merge_carlo.simulation.runner` 172/176 (97.7%), and
`merge_carlo.simulation.metrics` 278/285 (97.5%). The per-module table, the
recorded survivors and the runtime are in the
[mutation policy](mutation-policy.md).

The release workflows use separate build and publish jobs. They build with
`uv build`, check metadata with `twine check`, verify a SHA-256 manifest after
artifact transfer, and publish without a stored token through PyPI trusted
publishing. The PyPI and TestPyPI jobs receive `id-token: write` only at the
publish boundary. The local contract test, dry-run build, metadata check, and
workflow inspection passed for T-063. Later publisher configuration and the
v0.1.0 rehearsal are recorded above. Mutation testing is weekly asynchronous
assurance, not a release prerequisite; see [`releasing.md`](releasing.md).

The tests use synthetic inputs and saved or mocked HTTP responses. They verify
the offline demo is deterministic and does not construct network clients;
collection tests exercise reconciliation, interrupted/partial collections,
credential-safe errors and inspection of projected data. Generated experiment
reports carry their evidence status and model limitations, preserve null
unsupported safety fields, and are rendered from saved artifacts without
rerunning simulation. Saved summaries and reports expose requested, usable and
engine-truncated replication counts per assumption/scenario; any truncation
marks the whole comparison incomplete and the reader rejects inconsistent
counts (T-037).

## Limited or unverified

- **Authorized live GitHub integration has not been completed.** Bounded
  anonymous probes exercised five public repositories and found the expected
  incomplete-collection safeguards plus one calibration-to-simulation contract
  defect, fixed before T-063. No authorized dataset was
  collected for release evidence, so authorized collection, real-team
  calibration, and real-data validation remain unverified. Use the local
  [authorized-repository workflow](live-workflow.md) for the next run.
- The [performance benchmark](performance.md) is recorded for the synthetic demo
  workload on one machine (T-027). It supports no universal runtime, throughput,
  memory, or scalability claim, and summary memory grows with replication count.
- Held-out validation is historical and descriptive. It does not validate
  interventions, and small or incomplete evidence produces
  `insufficient_evidence`, not a pass.
- Reproducibility covers semantic artifacts in the locked reference environment,
  not arbitrary Python, NumPy, timezone-database, library, or hardware versions.
- Pseudonymized repository metadata can remain identifiable and must only be
  collected and shared with authorization.
- The recorded release mutation scores used mutmut 3.7.0. The current lock uses
  mutmut 3.8.0, which discovers decorated class bodies; decorated Pydantic
  validators and CLI command bodies remain verified by behavioral tests, not
  mutation testing (T-040, T-041). The current v0.1.0 floor is 70%; see the
  [mutation policy](mutation-policy.md). The historical full gate passed locally
  and in the GitHub workflow (run 34601538915, T-030). The historical host-dependent
  timezone and SQLite URI gaps were addressed by completed T-043; that old
  survivor table is not a current defect inventory.

## Unsupported in v0.1.0

- Productivity gain, business value, individual performance, safe
  auto-approval, causal intervention effects, exact future backlog, and a
  universal congestion threshold are not model outputs.
- `defect_escape_rate`, `security_risk_change`, and `policy_safety` remain
  `null` with reason `unsupported_in_v0_1`.
- Elapsed review delay is not active review effort. Active service remains an
  operator assumption and is never sampled from elapsed latency.
- The workflow model is CI-before-review with one required review and one FIFO
  queue; it is not GitHub branch-protection, CODEOWNERS, merge-queue, or
  multi-repository capacity emulation.

See [limitations](limitations.md) and the limitations section in every generated
experiment report for the complete qualifications.

## Remaining v0.1.0 work

T-064 is blocked and superseded after the v0.1.0 PyPI upload was cancelled.
T-067 owns v0.1.1 preparation, independent README/docs review, TestPyPI rehearsal,
and PyPI publication with clean-install and offline-demo verification. Trusted
publishers and protected environments are configured, but each publication
still requires maintainer approval. No authorized live dataset or verified
real-team calibration/real-data validation is included.

Deferred work outside the active spec includes:

- T-033 dataclass mutation coverage. The locked mutmut 3.8.0 discovers decorated
  class bodies. A T-063 in-memory discovery probe found 293 calendar mutants
  (135 in `DutyCalendar.materialize`) and 367 domain mutants (151 in
  `PullRequest.transition`); `@property` methods remain omitted. Discovery is
  not execution or efficacy evidence. Taskrail 0.4.0's supported `unblock`
  command returned T-033 to todo with a reason; its obsolete 3.7.0
  release-availability blocker is removed, not its remaining acceptance work.
- T-020 optional CI enrichment. v0.1.0 collection does not gather check-run or
  commit-status observations, so CI-derived estimates are unavailable.
- T-036 Taskrail reopening support. Taskrail 0.4.0 can unblock blocked tasks
  but cannot reopen completed work; completed T-028/T-029 history is preserved,
  with preparation and publication tracked separately in T-063/T-064.
- T-048 end-to-end held-out validation preparation under v0.2.0. A prepared
  real-data replay evidence workflow is not part of this release evidence.
- T-051 professional-workflow compatibility profiles under v0.3.0. The current
  simulator remains limited to its documented workflow assumptions.
