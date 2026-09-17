# Merge-carlo on Helm: simulation and holdout findings

This note records a real-data exercise against the public
[`helm/helm`](https://github.com/helm/helm) repository. It is an engineering
case study of data readiness and model fit, not a claim about Helm's team,
contributors, productivity, software quality, or policy safety.
It is exploratory research evidence, separate from the v0.1.0 release
evidence ledger; it does not retroactively establish live-integration support
for that release.

## Question and workflow

The exercise had two goals:

1. exercise the complete offline-first path on a substantial public repository;
2. determine whether the v0.1.0 workflow model describes the repository well
   enough for conditional scenario exploration.

The run used read-only collection and inspection, Python feature construction
and calibration, persisted simulation/report artifacts, and descriptive
validation. An earlier whole-period comparison was
kept as an `in_sample_diagnostic`. A second run used a chronological split so
that calibration did not inspect the validation outcomes:

| Interval | Use |
| --- | --- |
| 2025-01-01 through 2026-01-01 | fitting and calibration |
| 2026-01-01 through 2026-09-08 | held-out replay and mature outcomes |
| through 2026-09-15 | follow-up window for seven-day maturity |

The local evidence bundle is under
`.amp/in/artifacts/real-helm/holdout-2026-01-01/`. It is intentionally not
committed: the repository ignores `.amp/in/`, and the bundle contains generated
dataset and model artifacts rather than source documentation.

## Dataset readiness

The collection covered 1,938 pull requests, 5,911 reviews, 3,269 lifecycle
events, and 1,938 derived feature rows. Pull-request, review, and lifecycle
collections were complete. CI observations were not requested, so this run says
nothing about CI behavior.

The important limitations were:

- only 173 pull requests (8.9%) had an observed readiness event;
- 1,765 (91.1%) had unknown readiness and were excluded from strict
  ready-based fitting;
- the run used the explicit `created_at_proxy` readiness policy for the
  empirical arrival transformation;
- work origin was unknown for all 1,938 pull requests;
- 924 pull requests (47.7%) were unmerged and 204 (10.5%) remained open;
- 1,781 pull requests (91.9%) were excluded from lifecycle fitting, mostly for
  unknown readiness; and
- pull-request size was unavailable for every record.

These limitations make the calibration exploratory rather than a measured team
baseline. In particular, `created_at_proxy` is a declared proxy, not observed
readiness.

## Proper holdout results

The fitting interval contained 51 complete weeks and 758 benchmark
observations. The holdout contained 725 arrivals, of which 704 were mature
enough for the fixed seven-day outcome metrics. The replay used 100
replications. `merge-carlo validate --strict` returned exit code 4 because the
declared gates failed; the protocol itself was correctly `held_out`, not
`in_sample_diagnostic`.

The central comparison was:

| Metric | Observed eligibility | Observed | Mechanistic model | Elapsed-delay benchmark |
| --- | --- | ---: | ---: | ---: |
| Reviewed within 48 hours | mature holdout PRs, n=704 | 48.2% | 87.8% | 57.2% |
| Merged within 7 days | mature holdout PRs, n=704 | 45.6% | 100.0% | 54.8% |
| Median first review | completed first reviews, n=467 | 14.1 h | 11.4 h | 18.6 h |
| Weekly merges | complete holdout weeks, n=37 | 8 | 17 | 12 |
| Initial backlog | holdout boundary, n=1 | 87 | 0 | not applicable |

The mechanistic and benchmark columns summarize 100 replay replications; their
per-replication cohort sizes and variability are retained in the generated
validation report.

The elapsed-delay benchmark was closer for the two fixed-horizon shares and
weekly merge count; the mechanistic model was closer for median first review.
The benchmark is descriptive, not an intervention model: it resamples
historical delay and completion categories without adding a capacity queue.

## What the run establishes

The run shows that the CLI and artifact contracts can carry a real repository
through collection, inspection, calibration inputs, simulation, and descriptive
holdout validation. It also shows a model-fit failure under a temporal
protocol. That result is evidence to address the mismatch before making a
strong Helm-specific scenario claim.

The failure does **not** identify an engine defect. The discrepancies are
consistent with model-boundary and evidence limitations:

- v0.1 models a central FIFO review queue with a declared reviewer pool and a
  required review, while a professional repository may use routing, multiple
  approvals, protected branches, merge queues, and different closure rules;
- the v0.1 replay starts with no modeled backlog, while the observed holdout
  began with 87 items already in progress;
- the model's active review effort is an explicit assumption, not a measured
  service distribution inferred from elapsed review delay;
- observed close-without-merge and still-open work are retained in the data,
  but the v0.1 mechanistic path does not reproduce every repository-specific
  closure or merge-gating hazard; and
- unknown readiness, unknown work origin, absent CI observations, and missing
  size data limit what can be learned from calibration.

These are structural-fit hypotheses, not measured causes. The next step is to
expose them in reports and test declared workflow profiles, not silently tune
service time until historical percentages match.

## Roadmap implications

### v0.1.0

Keep the release boundary narrow. The immediate fixes are documentation and
truthfulness improvements:

- remove the stale `merge-carlo calibrate` CLI example; calibration remains a
  Python API in v0.1.0 (T-049);
- make fit diagnostics visibly distinguish a failed descriptive gate from
  initialization and unsupported workflow semantics (T-050); and
- retain the existing explicit `held_out` versus `in_sample_diagnostic`
  protocol labels.

These changes improve interpretation without changing the v0.1 simulator into
an enterprise workflow engine.

### v0.2.0

The end-to-end holdout preparation gap belongs here (T-048). A supported
workflow should create the chronological split, calibrate only on fitting data,
check mature follow-up, and bind the dataset, model, and replay inputs with
content hashes. The existing v0.2 quality contract also provides the correct
place for optional CI/static-analysis evidence, with separate evidence tiers
and no implicit defect labels.

### v0.3.0 and later

The non-blocking review model belongs in v0.3. It needs separate delivery and
post-delivery review lifecycles, review debt, follow-up work, and explicit
capacity accounting. Helm-like professional workflow dimensions should be
declared in a workflow profile and either modeled or marked unavailable:
approval count, reviewer routing, merge gating/queues, closure behavior,
initial backlog, and audit rules. A first v0.3 slice should not silently treat
unsupported dimensions as absent.

Full branch-protection emulation, arbitrary CODEOWNERS resolution, complex
merge-queue policies, and repository-specific policy optimization should remain
separate future scope unless a later specification supplies bounded contracts
and verification fixtures.

## Reproduction and interpretation

The generated validation report, rendered experiment report, model card, and
holdout metadata are the evidence for this note. Re-run the supported commands
from the repository documentation with an authorized collection and preserve
the resulting hashes. In the current v0.1.0 interface, collection and
inspection are CLI commands, but feature construction, calibration, and
holdout-evidence preparation use Python APIs; there is no supported single
`merge-carlo calibrate` command yet. The final `validate`, `simulate`, and
`report` steps consume the persisted artifacts. T-048 tracks the end-to-end
holdout preparation workflow, and T-049 tracks the stale command example in
the README. Do not copy that nonexistent command or commit credentials, raw
payloads, or generated SQLite datasets.

When reading the results, use these labels precisely:

- **observed**: a retained repository observation under the collection
  contract;
- **proxy/derived**: a transformation such as the explicit created-at
  readiness policy;
- **assumed**: an operator-supplied quantity such as active review effort; and
- **simulated**: an outcome of the declared model and random seed.

Neither the holdout failure nor the simulated scenario differences are causal
evidence. They are a decision to improve measurement and model scope before
making stronger claims.
