# Experiment artifacts

The Python API publishes an existing `simulation.runner.Experiment`:

```python
from pathlib import Path
from merge_carlo.artifacts import Evidence, write_experiment
from merge_carlo.reporting import render_report

# experiment is a caller-constructed, validated Experiment.
write_experiment(
    experiment,
    Evidence(synthetic=True, training_cutoff=None),
    Path("out/experiment"),
)
text = render_report(Path("out/experiment"))
```

This is not CLI wiring: `simulate` and `report` remain unimplemented commands.
Evidence status is caller-declared. `not_performed` is the validation default;
implementation tests do not imply historical or intervention validation.
For non-synthetic training templates, declare `template_basis` as `observed`,
`derived`, `proxy` or `assumed` (the conservative default). Synthetic experiments
always label their templates synthetic. Service, behavior, interventions and
availability in the current runner are declared assumptions.

Each JSON document or JSONL record carries `schema_version: 1`. JSON uses sorted
keys, ASCII escaping, compact separators, finite numbers, and a final newline.
No objects are pickled. Artifacts are:

| Artifact | Content |
| --- | --- |
| `manifest.json` | Application/model/schema versions, seed/keyed PCG64 scheme, timezone, dependency/Python versions, evidence status and SHA-256 hashes |
| `resolved-scenarios.json` | Entire resolved experiment, including baseline inputs, UTC bounds and elapsed durations; `demand_kinds` distinguishes additive from replacement transforms |
| `model-card.json` | Parameter-group provenance, distinct training-week count and unsupported risk/safety quantities |
| `replications.jsonl` | Streamed baseline/scenario metric pairs, identities, truncation flags and limitations |
| `paired-deltas.jsonl` | Per-replication all-work merge differences; relative difference is undefined for a zero baseline or truncated pair |
| `summary.json` | Separate assumption/scenario/population metric summaries, paired merge summaries and event probabilities |
| `summary.csv` | Long-form metric summaries with total, defined, excluded, median, central-90% bounds and undefined reason |
| `report.md` | Deterministic six-section report, read from `summary.json` |
| `traces.jsonl` | Only explicitly requested sampled engine diagnostics; empty by default, not a full transition log |

The manifest hashes every other file, including the report; it does not hash
itself. `dataset_content_hash` currently identifies the canonical serialized
training templates, not a SQLite file or an upstream collected dataset. Templates
must be normalized by the caller; template arrival order is part of proposal
identity. A future dataset pipeline must supply its own normalized source lineage.
Resolved dataclass JSON is an export contract, not yet an automatic replay loader;
reconstruct the `Experiment` using the exported values and demand kinds to rerun.

Summaries retain scalar metric values for exact run-level quantiles; they do not
pool individual PR latencies or retain all replication/trace objects. Baselines
are counted once per assumption and replication. Both `all_work` and `new_ready`
are preserved, including fixed-horizon total/eligible/excluded counts. Undefined
replication reasons remain in paired rows. Truncation excludes outcomes and marks
the comparison incomplete; no report ranks policies. T-037 owns the additional
prominent requested/usable/truncated comparison-count presentation.

Backlog exceedance and the share of paired runs with more merges use two-sided
95% Wilson intervals. These estimate conditional run-event probabilities, not
independent PR events. Central 90% summary ranges describe workflow variation;
Wilson intervals describe Monte Carlo error. Neither measures uncertainty about
the assumptions. The report does not pick a winning assumption or intervention.

CSV string cells beginning with `=`, `+`, `-`, `@`, tab, CR or LF are prefixed
with an apostrophe. Markdown metadata is escaped, including HTML and newlines.
JSON keeps original strings. Use only authorized, appropriately projected input:
resolved configurations and opt-in traces can retain actor identifiers. Reports
show aggregates, not individuals. The reader rejects unknown schema versions,
unknown contract fields, invalid counts/probability bounds/quantiles, and summary
files larger than 16 MiB. It does not authenticate who produced an artifact.

Publication is a single-writer local operation. A sibling temporary directory
holds the complete bundle before a rename exposes it. Nonempty destinations are
refused unless `overwrite=True`; files and symlinks are rejected. Explicit
overwrite first moves the old directory aside and restores it if publication
fails. Readers can see a brief missing-directory interval during overwrite, but
never partially written files. A process crash in that interval leaves the old
bundle under the sibling `-previous` name for recovery. This is not a concurrent
writer protocol or a power-loss durability guarantee.
