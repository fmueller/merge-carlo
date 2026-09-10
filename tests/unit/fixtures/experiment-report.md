# Experiment report — SYNTHETIC

## Question and evidence status — SYNTHETIC

How do declared workload and review-capacity scenarios change conditional review-system outcomes?

Validation: not_performed. Requested replications per assumption/scenario: 10. Comparison incomplete: true. No policy ranking is produced.

## Scenario comparison — SYNTHETIC

Load-response metrics: run-level median [central 90% range], not pooled PR observations. Undefined runs are excluded explicitly; null is not zero.

| Assumption | Scenario | Population.metric | Median [5%, 95%]; defined/requested |
| --- | --- | --- | --- |
| low | load | all&#95;work&#46;merges | 3 [1, 9]; 8/10 defined |
| low | load | all&#95;work&#46;backlog&#95;exceeded | 0 [0, 1]; 8/10 defined |

## Uncertainty and robustness — SYNTHETIC

Monte Carlo estimation error is separate from run-to-run variation and assumption uncertainty. Named assumption sets are not a probability distribution. All probabilities below are conditional on the model and the named assumption set. More merges is a direction, not a policy recommendation.

| Assumption | Scenario | Paired merge delta | Relative delta | Runs with more merges |
| --- | --- | --- | --- | --- |
| low | load | null [null, null]; 0/10 defined | null [null, null]; 0/10 defined | 0/0; null [95% Wilson: null, null] |

Backlog threshold exceedance (strictly above the declared threshold):

- low / load / all&#95;work&#46;backlog&#95;exceeded: 3/8; 0.375 [95% Wilson: 0.14, 0.69]

## Assumptions and data coverage — SYNTHETIC

Training cutoff: not supplied. See model-card.json for provenance and resolved-scenarios.json for exact parameters, calendars, local timezone and UTC bounds. Effort is assumed active service, never observed elapsed delay.

- engine&#95;truncated
- exploratory&#95;only

## Interpretation — SYNTHETIC

The model covers CI-before-review, one-required-review, a central FIFO queue and declared duty. It does not emulate branch protection. Latencies are completion-conditioned; read them alongside unresolved work and fixed-horizon shares. Warm-up from empty does not guarantee steady state. Truncated runs are excluded, never converted to favorable zero outcomes. Assumption-sensitive differences call for measuring active effort and availability, not selecting a winner. Historical fit is not causal validation. Removing review also removes modeled requested changes; flow differences are not net engineering benefit. No real GitHub action is taken.

defect_escape_rate: null; security_risk_change: null; policy_safety: null (reason for each: unsupported_in_v0_1).

## Reproduction — SYNTHETIC

manifest.json records versions, SHA-256 content hashes, seed, RNG scheme and evidence status. replications.jsonl and paired-deltas.jsonl preserve run-level values and undefined reasons. traces.jsonl contains only requested sampled engine diagnostics, not a full transition log. Re-render with merge_carlo.reporting.render_report(Path(results_directory)); this only reads artifacts. Reconstruct an Experiment manually from resolved-scenarios.json, including demand_kinds, then call merge_carlo.artifacts.write_experiment; there is no automatic replay loader. Reproducibility is limited to the locked reference environment, not arbitrary library versions or hardware. Metadata may remain identifiable; share only authorized data.
