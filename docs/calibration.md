# Empirical model calibration

`merge_carlo.calibration.calibrate_model` combines a frozen `FeatureSet` with
explicit active-review-effort assumptions and de-identified dataset coverage.
It returns a versioned model, a calibration record, and the inputs needed to
render a deterministic model card. `write_calibration` publishes `model.json`,
`calibration.json`, and `model-card.md` together into an empty or absent
directory. The persisted `simulate` command consumes the resulting `model.json`;
model calibration itself remains a Python API in v0.1.0, not a CLI command.

After `collect` and `inspect`, the exported projected dataset, a data-only
coverage record, explicit human-reviewer identifiers, and active-effort
assumptions are the calibration inputs. This is a complete API boundary; the
coverage and assumption files below are named inputs prepared by the caller:

```python
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from merge_carlo.calibration import (
    CalibrationCoverage,
    calibrate_model,
    load_assumptions,
    write_calibration,
)
from merge_carlo.features import build_features
from merge_carlo.store import ProjectedStore, WorkspaceKey

dataset_path = Path("data/cohort/dataset.sqlite")
workspace_path = Path("/private/path/merge-carlo-key")
coverage_path = Path("data/cohort/calibration-coverage.json")
assumptions_path = Path("configs/calibration-assumptions.json")
reviewers_path = Path("configs/human-reviewers.json")

with ProjectedStore(dataset_path, WorkspaceKey(workspace_path), existing_only=True) as store:
    extraction = store.manifests()[0]
    dataset = store.export(extraction.id)
    dataset_hash = store.content_hash(extraction.id)

coverage = CalibrationCoverage.model_validate_json(coverage_path.read_bytes())
if coverage.dataset_content_hash != dataset_hash:
    raise ValueError("coverage does not match the exported dataset")
assumptions = load_assumptions(json.loads(assumptions_path.read_text(encoding="utf-8")))
features = build_features(
    dataset,
    dataset_content_hash=dataset_hash,
    readiness_policy=coverage.readiness_policy,
    cutoff=datetime(2026, 7, 1, tzinfo=UTC),
    timezone="Europe/Berlin",
    outcome_horizon=timedelta(days=7),
    declared_human_reviewers=frozenset(json.loads(reviewers_path.read_text(encoding="utf-8"))),
)
result = calibrate_model(features, assumptions, coverage)
write_calibration(result, Path("models/repository"))
```

The output directory contains `model.json`, `calibration.json`, and
`model-card.md`. The model artifact is then consumed by the persisted
`simulate` command, and `report` reads only saved experiment and validation
artifacts:

```bash
uv run merge-carlo simulate --model models/repository/model.json \
  --scenarios configs/scenarios.yaml --out out/experiment
uv run merge-carlo report --results out/experiment \
  --validation out/validation/validation.json \
  --out out/experiment/report.md --overwrite
```

Active review effort is required for every declared work-origin cohort. It is
never inferred from first-review or ready-to-merge elapsed time. Supported
assumption distributions are a positive constant, a lognormal parameterized by
its median and log-space sigma, and a nonempty empirical sample of positive
seconds. Unknown keys and missing cohort assumptions are rejected. A mean and
sigma are not accepted as an alternative lognormal parameterization.

Every model parameter records its value specification, unit, provenance basis,
sample count, missingness treatment, grouping and fallback rule, evidence
references, and confidence-interval availability. Hand-entered assumptions have
no confidence interval unless a future contract explicitly declares one; the
current artifact records `null` with reason `not_declared`.

The default evidence safeguards are fewer than 30 usable pull requests, fewer
than 20 substantive decisions, fewer than eight complete local weeks, and more
than 20% unknown readiness. Thresholds are recorded in `calibration.json` and
may be replaced by explicit calibration inputs. Crossing any threshold adds its
specific flag and labels the model `exploratory_only`; equality passes. Empty
readiness coverage is excessive unknown evidence rather than a favorable zero.
Partial or unavailable pull-request, review, or lifecycle collection also keeps
the model exploratory; synthetic input is labeled `synthetic_demonstration`.

The readiness policy, basis counts, origin coverage, collection statuses, and
lifecycle exclusions are copied into calibration outputs. Unsupported v0.1.0
quantities — defect escape, security-risk change, and policy safety — remain
`null` with reason `unsupported_in_v0_1`. Model construction does not perform
held-out or intervention validation and makes no causal or productivity claim.
