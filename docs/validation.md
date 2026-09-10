# Held-out descriptive validation

`merge-carlo validate` applies configurable engineering gates to a prepared,
offline replay-evidence file. It does not fetch data, fit parameters, tune a
model, or rerun reporting artifacts. The producer freezes the model and
chronological split before inspecting held-out outcomes, replays the held-out
arrival timestamps, and supplies only attributes known when each arrival
occurred.

```bash
uv run merge-carlo validate --input out/replay-evidence.json --out out/validation
uv run merge-carlo validate --input out/replay-evidence.json --out out/validation --strict
```

The input is JSON with `schema_version: 1`. It records dataset identity, fitting
start and frozen training cutoff, half-open validation bounds, observed outcomes,
the frozen FIFO parameters, exact held-out arrivals, reviewer duty, seed,
replication count, thresholds, and joint historical review-delay and completion
observations for the elapsed-delay benchmark. The command runs the arrivals
through the existing FIFO engine; pre-aggregated simulated shares are not
accepted. The arrival contract contains only ID, author ID, declared work origin,
and readiness timestamp, so no future outcome attribute can enter the replay.
Each benchmark record includes its historical readiness and observed-through
timestamps. Its full observation interval must lie inside the fitting interval,
end no later than the frozen training cutoff, and provide at least seven days of
follow-up. Review and completion delays must fall inside that interval, and a
review cannot occur after the recorded merge or closure.

Unknown keys, scalar type coercions, naive timestamps, invalid counts, non-finite
values, and malformed probabilities are rejected. A validation interval starting
before the training cutoff is rejected unless `in_sample_diagnostic` is
explicitly true; such a result is labeled as an in-sample diagnostic rather than
held-out evidence.

The four historical descriptive comparisons are:

- mature-cohort reviewed-within-48-hours share;
- mature-cohort merged-within-seven-days share;
- median first-review elapsed seconds among completed first reviews; and
- weekly merge counts.

The output also gates the absolute difference between observed and simulated
initial backlog. If that discrepancy exceeds its tolerance, absolute backlog
forecasting is not supported. `validation.json` and `report.md` retain the exact
observed and simulated point estimates, observed and per-replication cohort
sizes, variability intervals, absolute errors, tolerances, and gate decisions.
The frozen model/capacity content and exact arrival list have separate canonical
SHA-256 bindings in the result and report.

The same report also shows an elapsed-delay resampling benchmark beside the
mechanistic FIFO description for all four historical comparisons. Each
replication samples joint historical records onto the exact held-out arrivals,
then applies the same 48-hour and seven-day mature cohorts, completion-conditioned
first-review metric, validation horizon, and local-week accounting. The sampled
records retain `merged`, `closed_without_merge`, and `not_completed` outcomes;
the per-replication category counts and source content hash are persisted.

This benchmark adds no capacity queue and must not be used to model an
intervention: it reuses observed elapsed delays, which include queueing and other
wall-clock effects rather than active review effort. The report always names the
description with lower point-estimate absolute error for each metric, including
when the elapsed-delay reference describes the held-out baseline better than the
mechanistic model. Both replication intervals remain visible; the label is not an
inferential claim that the difference is statistically distinguishable.

Too few mature pull requests, too few replay replications, or no simulated
first-review completions produces `insufficient_evidence`, never pass or fail.
A failed exploratory run still writes its artifacts and exits zero with a
warning. `--strict` changes only a `fail` exit to code 4; insufficient evidence
remains an explicit non-verdict.

This result is historical descriptive validation only. It does not establish
causal or intervention validity, productivity gain, policy safety, or safe
auto-approval. No parameter is automatically tuned against the held-out set.
