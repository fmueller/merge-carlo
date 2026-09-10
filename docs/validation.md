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
replication count, and thresholds. The command runs those arrivals through the
existing FIFO engine; pre-aggregated simulated shares are not accepted. The
arrival contract contains only ID, author ID, declared work origin, and readiness
timestamp, so no future outcome attribute can enter the replay.

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

Too few mature pull requests, too few replay replications, or no simulated
first-review completions produces `insufficient_evidence`, never pass or fail.
A failed exploratory run still writes its artifacts and exits zero with a
warning. `--strict` changes only a `fail` exit to code 4; insufficient evidence
remains an explicit non-verdict.

This result is historical descriptive validation only. It does not establish
causal or intervention validity, productivity gain, policy safety, or safe
auto-approval. No parameter is automatically tuned against the held-out set.
