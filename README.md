# merge-carlo

An offline-first scenario explorer for human and AI software-development
workflows. merge-carlo asks one question:

> How does additional AI-generated pull-request demand interact with constrained
> human review capacity, and which workflow interventions remain useful across
> plausible assumptions?

It imports read-only GitHub metadata, estimates what that data actually
supports, combines those estimates with explicitly declared assumptions, and
runs a discrete-event, agent-based simulation repeatedly under alternative
scenarios. The output is a comparison of **conditional simulated outcomes**, not
a causal estimate of AI productivity.

The agents are ordinary software objects with stochastic rules. They are not
language models, and no part of merge-carlo calls one.

## Status

Pre-alpha. The repository is set up and the v0.1.0 scope is frozen in
[`specs/v0.1.0.md`](specs/v0.1.0.md), but **the pipeline is not implemented
yet** — only `--version` and `--help` work today. Track progress in
[`docs/implementation-status.md`](docs/implementation-status.md) and
`planning/STATE.md`.

## What it does not do

- No LLM personas, agent frameworks, or automatic parameter tuning.
- No individual developer productivity scores, rankings, or inferred work hours.
- No AI-authorship classifier and no estimate of the fraction of AI-written code.
- No GitHub writes: no approvals, merges, labels, or reviewer assignment.
- No source-code ingestion, AST analysis, or learned risk score.
- No web dashboard, service, or database server.

Missing evidence, incomplete extraction, unknown attribution, and censored
outcomes stay visible in the output. Unsupported quantities are reported as
`null` with a reason, never as a favorable default.

## Install

```bash
uv sync --locked
```

Requires Python 3.12 or later (3.13 is the reference version).

## Use

The offline demo needs no credentials and makes no network calls:

```bash
uv run merge-carlo demo --out out/demo --seed 42 --replications 200
```

The real-data pipeline reads one explicitly selected repository. `GH_TOKEN`
comes from the environment or a secret manager; never put a token in a command,
configuration file, or report.

```bash
uv run merge-carlo collect   --repo OWNER/REPOSITORY --since 2026-04-01 --until 2026-09-01 --out data/repository.sqlite
uv run merge-carlo inspect   --dataset data/repository.sqlite --out out/inspection
uv run merge-carlo calibrate --dataset data/repository.sqlite --train-until 2026-07-01 \
                             --assumptions configs/team-assumptions.yaml --out models/repository
uv run merge-carlo validate  --dataset data/repository.sqlite --model models/repository/model.json \
                             --from 2026-07-01 --until 2026-08-01 --out out/validation
uv run merge-carlo simulate  --model models/repository/model.json --scenarios configs/scenarios.yaml --out out/experiment
uv run merge-carlo report    --results out/experiment --validation out/validation/validation.json \
                             --out out/experiment/report.md
```

Exit codes: `0` success, `2` invalid input, `3` source or access failure,
`4` a requested validation gate failed.

Dates define half-open UTC windows: `--until 2026-09-01` excludes September 1,
2026 and later events.

## Development

```bash
mise run setup          # pinned toolchain, locked dependencies, git hooks
mise run check          # the full local gate

uv run ruff check       # lint (--fix to autofix)
uv run ruff format      # format
uv run mypy             # type check
uv run pytest           # tests
```

Contributor rules are in [`CONTRIBUTING.md`](CONTRIBUTING.md); coding agents
read [`AGENTS.md`](AGENTS.md) first.

## Documentation

- [`specs/v0.1.0.md`](specs/v0.1.0.md) — the normative v0.1.0 scope boundary.
- [`docs/limitations.md`](docs/limitations.md) — what the model cannot establish.
- [`docs/implementation-status.md`](docs/implementation-status.md) — what is built and what is unverified.
- `specs/` — versioned specs; `planning/` — tracked work.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
