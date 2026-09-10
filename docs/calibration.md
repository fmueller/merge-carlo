# Empirical model calibration

`merge_carlo.calibration.calibrate_model` combines a frozen `FeatureSet` with
explicit active-review-effort assumptions and de-identified dataset coverage.
It returns a versioned model, a calibration record, and the inputs needed to
render a deterministic model card. `write_calibration` publishes `model.json`,
`calibration.json`, and `model-card.md` together into an empty or absent
directory. CLI wiring remains downstream work.

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
