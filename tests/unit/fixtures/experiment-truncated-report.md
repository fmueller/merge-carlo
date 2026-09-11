# Experiment report — SYNTHETIC

## Question and evidence status — SYNTHETIC

How do declared workload and review-capacity scenarios change conditional review-system outcomes?

Validation: not_performed. Requested replications per assumption/scenario: 2. Comparison incomplete: true. Policy ranking disabled: 1 of 6 runs engine-truncated, which marks the whole comparison incomplete.

Replication counts per assumption/scenario. An engine-truncated run contributes no outcome values, including merges before truncation; zero usable runs leave outcomes undefined, never zero.

| Assumption | Scenario | Requested | Usable | Engine-truncated |
| --- | --- | --- | --- | --- |
| fragile | baseline | 2 | 2 | 0 |
| fragile | bypass | 2 | 2 | 0 |
| fragile | load | 2 | 1 | 1 |

## Scenario comparison — SYNTHETIC

Load-response metrics: run-level median [central 90% range], not pooled PR observations. Undefined runs are excluded explicitly; null is not zero.

| Assumption | Scenario | Population.metric | Median [5%, 95%]; defined/requested |
| --- | --- | --- | --- |
| fragile | baseline | all&#95;work&#46;abandonments | 0 [0, 0]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;arrivals | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;backlog&#95;exceeded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;first&#95;review&#95;median | 7.5 [7.5, 7.5]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;first&#95;review&#95;p95 | 9.75 [9.75, 9.75]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;merged | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;merged&#46;eligible | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;merged&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;merged&#46;total | 2 [2, 2]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;merges | 2 [2, 2]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;queue&#95;peak | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;queue&#95;time&#95;average | 5.78704e-05 [5.78704e-05, 5.78704e-05]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;queue&#95;wait&#95;seconds | 5 [5, 5]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;ready&#95;to&#95;merge&#95;median | 17.5 [17.5, 17.5]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;ready&#95;to&#95;merge&#95;p95 | 19.75 [19.75, 19.75]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;requested&#95;changes | 0 [0, 0]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;review&#95;utilization | 0.00555556 [0.00555556, 0.00555556]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;reviewed | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;reviewed&#46;eligible | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;reviewed&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;reviewed&#46;total | 2 [2, 2]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;unresolved&#95;share | 0 [0, 0]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;unreviewed&#95;merges | 0 [0, 0]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;wip&#95;end | 0 [0, 0]; 2/2 defined |
| fragile | baseline | all&#95;work&#46;wip&#95;start | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;abandonments | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;arrivals | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;backlog&#95;exceeded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;first&#95;review&#95;median | 5 [5, 5]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;first&#95;review&#95;p95 | 5 [5, 5]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;merged | null [null, null]; 0/2 defined |
| fragile | baseline | new&#95;ready&#46;merged&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;merged&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;merged&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;merges | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;queue&#95;peak | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;queue&#95;time&#95;average | 5.78704e-05 [5.78704e-05, 5.78704e-05]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;queue&#95;wait&#95;seconds | 5 [5, 5]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;ready&#95;to&#95;merge&#95;median | 15 [15, 15]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;ready&#95;to&#95;merge&#95;p95 | 15 [15, 15]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;requested&#95;changes | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;review&#95;utilization | 0.00277778 [0.00277778, 0.00277778]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;reviewed | null [null, null]; 0/2 defined |
| fragile | baseline | new&#95;ready&#46;reviewed&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;reviewed&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;reviewed&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;unresolved&#95;share | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;unreviewed&#95;merges | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;wip&#95;end | 0 [0, 0]; 2/2 defined |
| fragile | baseline | new&#95;ready&#46;wip&#95;start | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;abandonments | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;arrivals | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;backlog&#95;exceeded | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;first&#95;review&#95;median | null [null, null]; 0/2 defined |
| fragile | bypass | all&#95;work&#46;first&#95;review&#95;p95 | null [null, null]; 0/2 defined |
| fragile | bypass | all&#95;work&#46;merged | null [null, null]; 0/2 defined |
| fragile | bypass | all&#95;work&#46;merged&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;merged&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;merged&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;merges | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;queue&#95;peak | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;queue&#95;time&#95;average | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;queue&#95;wait&#95;seconds | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;ready&#95;to&#95;merge&#95;median | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;ready&#95;to&#95;merge&#95;p95 | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;requested&#95;changes | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;review&#95;utilization | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;reviewed | null [null, null]; 0/2 defined |
| fragile | bypass | all&#95;work&#46;reviewed&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;reviewed&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;reviewed&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;unresolved&#95;share | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;unreviewed&#95;merges | 1 [1, 1]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;wip&#95;end | 0 [0, 0]; 2/2 defined |
| fragile | bypass | all&#95;work&#46;wip&#95;start | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;abandonments | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;arrivals | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;backlog&#95;exceeded | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;first&#95;review&#95;median | null [null, null]; 0/2 defined |
| fragile | bypass | new&#95;ready&#46;first&#95;review&#95;p95 | null [null, null]; 0/2 defined |
| fragile | bypass | new&#95;ready&#46;merged | null [null, null]; 0/2 defined |
| fragile | bypass | new&#95;ready&#46;merged&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;merged&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;merged&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;merges | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;queue&#95;peak | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;queue&#95;time&#95;average | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;queue&#95;wait&#95;seconds | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;ready&#95;to&#95;merge&#95;median | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;ready&#95;to&#95;merge&#95;p95 | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;requested&#95;changes | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;review&#95;utilization | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;reviewed | null [null, null]; 0/2 defined |
| fragile | bypass | new&#95;ready&#46;reviewed&#46;eligible | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;reviewed&#46;excluded | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;reviewed&#46;total | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;unresolved&#95;share | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;unreviewed&#95;merges | 1 [1, 1]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;wip&#95;end | 0 [0, 0]; 2/2 defined |
| fragile | bypass | new&#95;ready&#46;wip&#95;start | 0 [0, 0]; 2/2 defined |
| fragile | load | all&#95;work&#46;abandonments | 0 [0, 0]; 1/2 defined |
| fragile | load | all&#95;work&#46;arrivals | 2 [2, 2]; 1/2 defined |
| fragile | load | all&#95;work&#46;backlog&#95;exceeded | 1 [1, 1]; 1/2 defined |
| fragile | load | all&#95;work&#46;first&#95;review&#95;median | 17.5 [17.5, 17.5]; 1/2 defined |
| fragile | load | all&#95;work&#46;first&#95;review&#95;p95 | 24.25 [24.25, 24.25]; 1/2 defined |
| fragile | load | all&#95;work&#46;merged | 1 [1, 1]; 1/2 defined |
| fragile | load | all&#95;work&#46;merged&#46;eligible | 2 [2, 2]; 1/2 defined |
| fragile | load | all&#95;work&#46;merged&#46;excluded | 2 [2, 2]; 1/2 defined |
| fragile | load | all&#95;work&#46;merged&#46;total | 4 [4, 4]; 1/2 defined |
| fragile | load | all&#95;work&#46;merges | 4 [4, 4]; 1/2 defined |
| fragile | load | all&#95;work&#46;queue&#95;peak | 3 [3, 3]; 1/2 defined |
| fragile | load | all&#95;work&#46;queue&#95;time&#95;average | 0.000578704 [0.000578704, 0.000578704]; 1/2 defined |
| fragile | load | all&#95;work&#46;queue&#95;wait&#95;seconds | 50 [50, 50]; 1/2 defined |
| fragile | load | all&#95;work&#46;ready&#95;to&#95;merge&#95;median | 27.5 [27.5, 27.5]; 1/2 defined |
| fragile | load | all&#95;work&#46;ready&#95;to&#95;merge&#95;p95 | 34.25 [34.25, 34.25]; 1/2 defined |
| fragile | load | all&#95;work&#46;requested&#95;changes | 0 [0, 0]; 1/2 defined |
| fragile | load | all&#95;work&#46;review&#95;utilization | 0.0111111 [0.0111111, 0.0111111]; 1/2 defined |
| fragile | load | all&#95;work&#46;reviewed | 1 [1, 1]; 1/2 defined |
| fragile | load | all&#95;work&#46;reviewed&#46;eligible | 2 [2, 2]; 1/2 defined |
| fragile | load | all&#95;work&#46;reviewed&#46;excluded | 2 [2, 2]; 1/2 defined |
| fragile | load | all&#95;work&#46;reviewed&#46;total | 4 [4, 4]; 1/2 defined |
| fragile | load | all&#95;work&#46;unresolved&#95;share | 0 [0, 0]; 1/2 defined |
| fragile | load | all&#95;work&#46;unreviewed&#95;merges | 0 [0, 0]; 1/2 defined |
| fragile | load | all&#95;work&#46;wip&#95;end | 0 [0, 0]; 1/2 defined |
| fragile | load | all&#95;work&#46;wip&#95;start | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;abandonments | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;arrivals | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;backlog&#95;exceeded | 1 [1, 1]; 1/2 defined |
| fragile | load | new&#95;ready&#46;first&#95;review&#95;median | 20 [20, 20]; 1/2 defined |
| fragile | load | new&#95;ready&#46;first&#95;review&#95;p95 | 24.5 [24.5, 24.5]; 1/2 defined |
| fragile | load | new&#95;ready&#46;merged | null [null, null]; 0/2 defined |
| fragile | load | new&#95;ready&#46;merged&#46;eligible | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;merged&#46;excluded | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;merged&#46;total | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;merges | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;queue&#95;peak | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;queue&#95;time&#95;average | 0.000462963 [0.000462963, 0.000462963]; 1/2 defined |
| fragile | load | new&#95;ready&#46;queue&#95;wait&#95;seconds | 40 [40, 40]; 1/2 defined |
| fragile | load | new&#95;ready&#46;ready&#95;to&#95;merge&#95;median | 30 [30, 30]; 1/2 defined |
| fragile | load | new&#95;ready&#46;ready&#95;to&#95;merge&#95;p95 | 34.5 [34.5, 34.5]; 1/2 defined |
| fragile | load | new&#95;ready&#46;requested&#95;changes | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;review&#95;utilization | 0.00555556 [0.00555556, 0.00555556]; 1/2 defined |
| fragile | load | new&#95;ready&#46;reviewed | null [null, null]; 0/2 defined |
| fragile | load | new&#95;ready&#46;reviewed&#46;eligible | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;reviewed&#46;excluded | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;reviewed&#46;total | 2 [2, 2]; 1/2 defined |
| fragile | load | new&#95;ready&#46;unresolved&#95;share | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;unreviewed&#95;merges | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;wip&#95;end | 0 [0, 0]; 1/2 defined |
| fragile | load | new&#95;ready&#46;wip&#95;start | 0 [0, 0]; 1/2 defined |

## Uncertainty and robustness — SYNTHETIC

Monte Carlo estimation error is separate from run-to-run variation and assumption uncertainty. Named assumption sets are not a probability distribution. All probabilities below are conditional on the model and the named assumption set. More merges is a direction, not a policy recommendation.

| Assumption | Scenario | Paired merge delta | Relative delta | Runs with more merges |
| --- | --- | --- | --- | --- |
| fragile | bypass | -1 [-1, -1]; 2/2 defined | -0.5 [-0.5, -0.5]; 2/2 defined | 0/2; 0 [95% Wilson: 0, 0.65762] |
| fragile | load | 2 [2, 2]; 1/2 defined | 1 [1, 1]; 1/2 defined | 1/1; 1 [95% Wilson: 0.206549, 1] |

Backlog threshold exceedance (strictly above the declared threshold):

- fragile / baseline / all&#95;work&#46;backlog&#95;exceeded: 2/2; 1 [95% Wilson: 0.34238, 1]
- fragile / baseline / new&#95;ready&#46;backlog&#95;exceeded: 2/2; 1 [95% Wilson: 0.34238, 1]
- fragile / bypass / all&#95;work&#46;backlog&#95;exceeded: 0/2; 0 [95% Wilson: 0, 0.65762]
- fragile / bypass / new&#95;ready&#46;backlog&#95;exceeded: 0/2; 0 [95% Wilson: 0, 0.65762]
- fragile / load / all&#95;work&#46;backlog&#95;exceeded: 1/1; 1 [95% Wilson: 0.206549, 1]
- fragile / load / new&#95;ready&#46;backlog&#95;exceeded: 1/1; 1 [95% Wilson: 0.206549, 1]

## Assumptions and data coverage — SYNTHETIC

Training cutoff: 2026&#45;09&#45;07T00:00:00Z. See model-card.json for provenance and resolved-scenarios.json for exact parameters, calendars, local timezone and UTC bounds. Effort is assumed active service, never observed elapsed delay.

- engine&#95;truncated
- exploratory&#95;only

## Interpretation — SYNTHETIC

The model covers CI-before-review, one-required-review, a central FIFO queue and declared duty. It does not emulate branch protection. Latencies are completion-conditioned; read them alongside unresolved work and fixed-horizon shares. Warm-up from empty does not guarantee steady state. Truncated runs are excluded, never converted to favorable zero outcomes. Assumption-sensitive differences call for measuring active effort and availability, not selecting a winner. Historical fit is not causal validation. Removing review also removes modeled requested changes; flow differences are not net engineering benefit. No real GitHub action is taken.

defect_escape_rate: null; security_risk_change: null; policy_safety: null (reason for each: unsupported_in_v0_1).

## Reproduction — SYNTHETIC

manifest.json records versions, SHA-256 content hashes, seed, RNG scheme and evidence status. replications.jsonl and paired-deltas.jsonl preserve run-level values and undefined reasons. traces.jsonl contains only requested sampled engine diagnostics, not a full transition log. Re-render with merge_carlo.reporting.render_report(Path(results_directory)); this only reads artifacts. Reconstruct an Experiment manually from resolved-scenarios.json, including demand_kinds, then call merge_carlo.artifacts.write_experiment; there is no automatic replay loader. Reproducibility is limited to the locked reference environment, not arbitrary library versions or hardware. Metadata may remain identifiable; share only authorized data.
