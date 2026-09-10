<h1>
  <img src="assets/logo.svg" alt="" width="44">
  merge-carlo
</h1>

[![Build](https://github.com/fmueller/merge-carlo/actions/workflows/build.yml/badge.svg)](https://github.com/fmueller/merge-carlo/actions/workflows/build.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/fmueller/merge-carlo/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

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
[`specs/v0.1.0.md`](specs/v0.1.0.md). **The offline synthetic demo works;
the real-data pipeline is not implemented yet.** Track progress in
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

After dependencies are installed, use `uv run --offline --no-sync` (or
`.venv/bin/merge-carlo`) to prevent the package manager from accessing the
network too. The output directory must be empty or absent; use another directory
to rerun. The same seed and locked environment reproduce identical artifacts.

Open `out/demo/report.md`. Every major section is labeled **SYNTHETIC** and
states that only the base assumption set was run, not full sensitivity. The
versioned `resolved-scenarios.json` includes the synthetic dataset under
`experiment.templates`, example assumptions under `experiment.assumptions`,
and scenario overrides under `experiment.scenarios` (baseline is implicit).
The suite demonstrates additive AI demand, AI replacement, extended review duty,
a dated reviewer absence, and hypothetical review bypass. Model card, manifest,
summary JSON/CSV, replication rows and paired deltas accompany the report;
`traces.jsonl` is empty because full diagnostics are opt-in.

These are illustrative inputs, not measured behavior or a policy recommendation.
The two synthetic weeks are exploratory; active review service is an assumed
constant. Replacement changes origin only and does not imply different effort.

The following real-data commands are planned, **not yet available**.
The real-data pipeline will read one explicitly selected repository. `GH_TOKEN`
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
- [`docs/brand.md`](docs/brand.md) — the two marks, where each one is used, and the palette.
- `specs/` — versioned specs; `planning/` — tracked work.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
