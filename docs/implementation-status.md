# Implementation status

This is the v0.1.0 evidence ledger: what is implemented, what was verified, what
is limited or unsupported, and what remains. “Implemented” does not imply that a
model is validated for a real workflow or that the release is ready to publish.

Last updated: 2026-09-11.

## Milestones

| Milestone | Scope | Status |
| --- | --- | --- |
| M0 | Packaging, pinned toolchain, CI, commit policy, spec and backlog | Complete |
| M1 | Domain contracts, duty calendars and deterministic FIFO engine | Complete |
| M2 | Keyed randomness, revisions, abandonment, demand/capacity scenarios and bypass | Complete |
| M3 | Replication runner, metrics, artifacts, report and synthetic demo | Limited: truncation reporting and real-data CLI remain |
| M4 | Read-only transport/store, cohort collection, attribution and inspection | Implemented; optional CI enrichment deferred to v0.2.0 |
| M5 | Frozen features, provenance-tagged calibration and descriptive validation/benchmark | Complete through Python APIs and offline validation CLI |
| M6 | Schemas, release evidence, performance benchmark, mutation gate and publishing | In progress |

## Implemented command surface

`merge-carlo` exposes `schema`, `demo`, `collect`, `inspect`, and `validate`, plus
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

The release-documentation change was checked from `origin/main` at
`16da175d7c9a6d2dc6b14956ad5b74274ebfd445`. The final evidence is recorded by
command rather than summarized as an unsupported readiness claim:

| Command | Result | Evidence covered |
| --- | --- | --- |
| `uv run pytest tests/unit/cli_test.py tests/unit/documentation_test.py -q` | Pass: 21 | Help, JSON console records, exit codes and documentation contract |
| `uv run pytest tests/unit/cli_test.py tests/unit/cohort_test.py tests/unit/inspection_test.py tests/integration/demo_test.py -q` | Pass: 54 | Fixture-backed command pipeline, resume and partial-data behavior |
| `uv run ruff check` and `uv run ruff format --check` | Pass | Lint and formatting |
| `uv run mypy` | Pass: 53 source files | Strict type checking |
| `uv run pytest` | Pass: 620 | Full automated suite |
| `mise run test:mutate` | Pass: `merge_carlo.cli` 74/90 (82.2%) | Differential v0.1.0 mutation policy for changed executable source |
| `mise run check` | Pass | CI-equivalent local gate |

The release mutation gate (T-030) was run separately on 2026-09-11:
`mise run test:mutate:gate` passed with every one of 22 modules at or above the
80% floor, including `merge_carlo.simulation.engine` 601/613 (98.0%),
`merge_carlo.simulation.runner` 172/176 (97.7%), and
`merge_carlo.simulation.metrics` 278/285 (97.5%). The per-module table, the
recorded survivors and the runtime are in the
[mutation policy](mutation-policy.md).

The tests use synthetic inputs and saved or mocked HTTP responses. They verify
the offline demo is deterministic and does not construct network clients;
collection tests exercise reconciliation, interrupted/partial collections,
credential-safe errors and inspection of projected data. Generated experiment
reports carry their evidence status and model limitations, preserve null
unsupported safety fields, and are rendered from saved artifacts without
rerunning simulation. Comparison-wide truncation counts and gating are not
complete until T-037 lands.

## Limited or unverified

- **Live GitHub integration has not been run.** No authorized dataset was
  collected for this release work, so collection against GitHub, real-team
  calibration, and real-data validation remain unverified.
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
- Mutation scores cover only the functions mutmut 3.7.0 instruments. Decorated
  Pydantic validators and CLI command bodies are verified by behavioral tests,
  not mutation testing (T-040, T-041); see the
  [mutation policy](mutation-policy.md). The full mutation gate passed locally
  and in the GitHub workflow (run 34601538915, T-030). Seven timezone and five
  SQLite URI mutants are killed locally but survive on CI because those tests
  depend on the host (T-043).

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

The open tracked v0.1.0 tasks are T-029 trusted release publishing, T-037
comparison truncation propagation, T-039 persisted experiment CLI wiring, and
T-043 host-independent timezone and SQLite URI mutation kills. Their presence means v0.1.0 should not be
described as fully complete or published.

Three tasks are deferred to the inactive v0.2.0 draft spec:

- T-033 dataclass mutation discovery. mutmut 3.7.0 does not mutate methods of
  decorated classes, so v0.1.0 per-module mutation scores do not cover
  `@dataclass` methods such as `DutyCalendar.materialize` or
  `PullRequest.transition`.
- T-020 optional CI enrichment. v0.1.0 collection does not gather check-run or
  commit-status observations, so CI-derived estimates are unavailable.
- T-036 Taskrail reopening support, a repository tooling follow-up rather than
  simulator behavior.
