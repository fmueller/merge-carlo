# Local authorized-repository workflow

Use [`scripts/run_live_workflow.py`](../scripts/run_live_workflow.py) on a
machine where a read-only `GITHUB_TOKEN` is available. The script runs the
existing collect, inspect, Python feature/calibration, and persisted simulate
interfaces for up to five repositories. It never accepts a token as a command
argument and never writes the token to an artifact.

```bash
export GITHUB_TOKEN='token kept in the shell environment'
uv run python scripts/run_live_workflow.py \
  --repo markupsafe/markupsafe \
  --repo helm/helm \
  --repo fastapi/fastapi \
  --repo pandas-dev/pandas \
  --repo github/codeql \
  --out out/live
```

With no `--repo`, those five repositories are the defaults. The default window
is `[2026-04-01T00:00:00Z, 2026-09-01T00:00:00Z)` and the training cutoff is
the interval midpoint. Override dates, limits, timezone, and the scenario YAML
with the script's `--help` options. The default active-effort input is a
lognormal assumption with median 900 seconds and log-space sigma 0.4 for every
declared work-origin cohort; it is an operator assumption, not an estimate from
elapsed review delay. Pass `--assumptions path.json` to replace it.

Work origin and human-review status are not inferred from GitHub account type.
Pass a JSON array of pseudonymous reviewer IDs with `--human-reviewers`, or
repeat `--human-reviewer`. If none are supplied, the run still produces a
valid but exploratory model with zero declared human decisions. Each repository
also gets `inputs/reviewer-candidates.json`; select IDs from that file and use a
fresh output directory for a rerun with an explicit reviewer roster. The
default private key is `~/.local/share/merge-carlo/workspace/actor.key` (or the
path supplied to `--workspace`); keep it private because it stabilizes actor
pseudonyms across extractions.

Each repository directory contains:

- `dataset/dataset.sqlite`: the projected, allowlisted dataset;
- `inspection/report.md` and `inspection/inspection.json`: coverage evidence;
- `inputs/calibration-coverage.json`, the resolved assumptions, and the
  selected pseudonymous `human-reviewers.json` roster;
- `model/model.json`, `calibration.json`, and `model-card.md` after calibration;
- `experiment/report.md` and the saved simulation artifacts; and
- `inputs/reviewer-candidates.json` for explicit roster preparation.

`summary.md` and `summary.json` link these artifacts. Partial or unavailable
pull-request, review, or lifecycle collections stop that repository before
feature construction and calibration; no successful report is fabricated. A
simulation report is not held-out validation. Preparing replay evidence and
running `merge-carlo validate --strict` remain separate because v0.1 does not
infer intervention validity from an in-sample simulation.

The runner is intended for authorized local release testing. Do not publish the
dataset, private workspace, reviewer roster, or repository-specific model
artifacts without the repository owner's authorization.
