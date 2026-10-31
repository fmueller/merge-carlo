<h1>
  <img src="https://raw.githubusercontent.com/fmueller/merge-carlo/60eaf6e5482991f30cfc3b7ffcce922389d258b9/assets/logo.svg" alt="" width="44">
  merge-carlo
</h1>

[![Build](https://github.com/fmueller/merge-carlo/actions/workflows/build.yml/badge.svg)](https://github.com/fmueller/merge-carlo/actions/workflows/build.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/fmueller/merge-carlo/blob/v0.1.1/pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/fmueller/merge-carlo/blob/v0.1.1/LICENSE)

An offline-first scenario explorer for pull-request review workflows.

> How does additional AI-generated pull-request demand interact with constrained
> human review capacity, and which workflow interventions remain useful across
> plausible assumptions?

merge-carlo combines read-only GitHub metadata with explicit assumptions and
runs repeated discrete-event simulations under alternative scenarios. It
compares **conditional simulated outcomes**, not causal AI productivity gains.
Its agents are ordinary software objects with stochastic rules, not language
models. No part of merge-carlo calls an LLM or writes to GitHub.

## Install

Requires Python 3.12–3.14. Install the CLI in an isolated environment with
[uv](https://docs.astral.sh/uv/):

```bash
uv tool install merge-carlo==0.1.1
```

Alternatively, run `python -m pip install merge-carlo==0.1.1` in a virtual
environment. Installation downloads dependencies; the demo itself is offline.

## First offline run

No credentials, repository checkout, or network access are needed after installation:

```bash
merge-carlo demo --out out/demo --seed 42 --replications 200
```

Open `out/demo/report.md`. It compares a baseline with additive AI demand, AI
replacement, extended review duty, a reviewer absence, and hypothetical review
bypass. The output includes review latency, throughput, queueing, uncertainty,
and paired scenario deltas, alongside a model card and JSON/CSV artifacts.

Every major report section is labeled **SYNTHETIC**. The demo runs only the base
assumption set, not full sensitivity analysis. Its two synthetic weeks are
illustrative inputs, not measured team behavior or a policy recommendation.
Active review effort is assumed; replacement changes origin only, not effort.

The output directory must be empty or absent; choose another directory to
rerun. A fixed seed reproduces artifacts within the same dependency environment.
For a locked development environment, see the
[contributor guide](https://github.com/fmueller/merge-carlo/blob/v0.1.1/CONTRIBUTING.md).

## Status and limits

**Pre-alpha.** The offline demo, read-only collection, dataset inspection,
Python API calibration, held-out descriptive validation, and persisted
simulation/reporting are implemented. Calibration is a Python API, not a CLI
subcommand. See [implementation status](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/implementation-status.md)
for evidence and remaining gaps.

**Authorized live GitHub integration has not been completed.** No authorized
dataset was collected for release evidence. Live collection, real-team
calibration, and real-data validation remain unverified; synthetic fixtures and
anonymous failure-path probes do not establish them.

- No developer productivity scores, rankings, or inferred work hours.
- No AI-authorship classifier; unknown work origin stays unknown.
- No GitHub approvals, merges, labels, or reviewer assignment.
- No source-code ingestion, LLM personas, automatic parameter tuning, or web dashboard.
- No claim about defect escape, security risk, or the safety of review bypass.

Missing evidence, incomplete extraction, censoring, and unsupported quantities
stay visible. Unsupported metrics are `null` with a reason, never favorable
defaults. Read the [model limitations](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/limitations.md)
before interpreting a scenario comparison.

## Work with repository data

The supported path is `collect` → `inspect` → Python API calibration →
`simulate` → `report`, with `validate` for prepared held-out replay evidence.
Collection needs authorized GitHub access; subsequent analysis uses local
artifacts. Calibration inputs and held-out evidence must be prepared explicitly,
not inferred by a one-command pipeline.

### Collect and inspect

Read-only [cohort collection](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/cohort-collection.md)
reads one explicitly selected, authorized repository. Supply `GITHUB_TOKEN`
through the environment, never a command argument or configuration file. Keep
the private workspace key outside the dataset:

```bash
merge-carlo collect --repo OWNER/REPOSITORY \
  --start 2026-04-01T00:00:00Z --end 2026-09-01T00:00:00Z \
  --out data/cohort --workspace /private/path/merge-carlo-key
```

The cohort includes PRs created in `[start, end)` and older PRs whose open or
closing evidence overlaps that interval. `--end 2026-09-01T00:00:00Z` excludes
PR creations at or after September 1; it does not truncate retained PRs' review
or lifecycle history. Repeat with `--resume` to reconcile from page one.
Incomplete collections exit 3 and retain explicit statuses. Readiness defaults
to strict evidence handling; work origin stays unknown unless locally declared.

Inspect the dataset without the private key. This writes `inspection.json`
and `report.md` with coverage, missingness, censoring, and extraction limitations:

```bash
merge-carlo inspect --dataset data/cohort/dataset.sqlite --out out/inspection
```

### Calibrate, validate, and compare

Follow the [Python calibration guide](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/calibration.md)
to prepare coverage, reviewer, and effort-assumption inputs and write
`models/repository/model.json`, `calibration.json`, and `model-card.md`.
Active review effort is an explicit assumption, **never inferred from elapsed
review delay**.

With a prepared, versioned held-out replay evidence file, run descriptive
validation. By default failed gates are warnings; `--strict` exits 4 when a
declared criterion fails:

```bash
merge-carlo validate --input out/replay-evidence.json --out out/validation --strict
```

See [validation](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/validation.md)
for the evidence contract. Then simulate the saved model and generate a report
from the result artifacts, without rerunning the simulation:

```bash
merge-carlo simulate --model models/repository/model.json \
  --scenarios configs/scenarios.yaml --out out/experiment
merge-carlo report --results out/experiment \
  --validation out/validation/validation.json \
  --out out/experiment/report.md --overwrite
```

Export the assumption and scenario schemas before authoring configuration:

```bash
merge-carlo schema --out out/schemas
```

Use the [configuration guide](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/configuration.md)
and [data-only examples](https://github.com/fmueller/merge-carlo/tree/v0.1.1/examples).
For collection through reporting across selected repositories, see the
[authorized local workflow](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/live-workflow.md).
It reports blocked results when evidence is incomplete; it does not establish
that live integration has already succeeded.

### Automation

Exit codes: `0` success, `2` invalid input, `3` source or access failure,
`4` a requested validation gate failed.

Add global `--json` before a command for machine-readable console output:

```bash
merge-carlo --json schema --out out/schemas
```

Each operational result or error is one JSON object containing `status`,
`exit_code`, and `message`. Errors move from stderr to stdout in this mode;
help remains human-readable. Exit codes and artifact contents are unchanged.

## Development

Clone the repository for the pinned toolchain, locked dependencies, and tests:

```bash
git clone https://github.com/fmueller/merge-carlo.git
cd merge-carlo
mise run setup
mise run check
```

Inside the checkout, use `uv run merge-carlo` instead of the installed CLI.
After setup, `uv run --offline --no-sync merge-carlo` also prevents package
manager network access. See [contributing](https://github.com/fmueller/merge-carlo/blob/v0.1.1/CONTRIBUTING.md);
coding agents read [AGENTS.md](https://github.com/fmueller/merge-carlo/blob/v0.1.1/AGENTS.md) first.

## Documentation

- [Configuration and scenarios](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/configuration.md)
- [Calibration](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/calibration.md)
- [Collection and data handling](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/cohort-collection.md)
- [Validation](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/validation.md)
- [Model limitations](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/limitations.md)
- [Performance measurements](https://github.com/fmueller/merge-carlo/blob/v0.1.1/docs/performance.md)
- [Normative v0.1 scope](https://github.com/fmueller/merge-carlo/blob/v0.1.1/specs/v0.1.0.md)
- [Research and references](https://github.com/fmueller/merge-carlo/tree/v0.1.1/docs/research)

## License

Apache-2.0. See [LICENSE](https://github.com/fmueller/merge-carlo/blob/v0.1.1/LICENSE).
