# Limitations

merge-carlo produces conditional simulated outcomes. This file records what it
cannot establish. Keep it current as milestones land; every generated report
must be readable alongside it.

## What the model is

The simulated system begins when a pull request is **ready for review** and ends
at merge, close-without-merge, or the observation horizon. Initial task
discovery and coding are outside the boundary. merge-carlo therefore tests the
review-system consequences of an assumed pull-request workload. It does not
estimate coding-time savings or the number of valuable tasks a team completes.

## Identifiability

Observed elapsed review time decomposes into eligibility and coordination delay,
calendar delay, queue waiting, active review service, and other unobserved
delay. Nothing in GitHub metadata separates those components. The decomposition
is a modeling assumption, and active review effort is a **declared assumption**,
never an inference from elapsed latency.

Different combinations of effort, staffing, and coordination delay reproduce
similar latencies. v0.1.0 deliberately ships no optimizer that picks one of
them.

## Workflow class

The implemented deterministic `simulation.engine.run_fifo` slice accepts fresh
READY proposals and a declared constant service duration (at least one second,
rounded up). Readiness is elapsed seconds from a supplied UTC span's start.
Reviewers supply sorted, disjoint UTC duty intervals, normally materialized by
`DutyCalendar`. Inputs are not mutated and output ordering is stable by ID.
`RevisionLoops` supplies assumed constant elapsed verification and author-response
delays, a verification-failure probability, and separate first/repeat review
requested-change probabilities. These are assumptions, not observed effort.
Verification runs concurrently without a runner queue and outside reviewer duty.
Failures and requested changes cause an author response, a new revision and a
new verification gate. Defaults preserve instant verification and approval;
review approval still merges instantly. Abandonment scheduling remains tracked
v0.1.0 work (T-008); this slice rejects prior state and abandonment deadlines.

Inclusive per-proposal limits bound review visits and verification attempts
across all revisions (both default to 100). Attempting further work stops the
whole replication with `engine_truncated`, retaining diagnostic state and
consumed service, without inventing abandonment or horizon censoring.
`summarize_replications` excludes the entire truncated run, including earlier
merges, exposes `engine_truncated_count`, marks the comparison incomplete and
disables policy ranking. With no usable replications its outcome counts are
`None`, not zero. Its pooled merge/unresolved counts are a Python API primitive;
CLI artifacts, comparison-wide propagation and additional validity gates remain
downstream work. Passing this truncation gate alone does not justify ranking.

The run is half-open: arrivals at or beyond the horizon are excluded and a
completion exactly at the horizon is censored, with all preceding active
service retained. Equal-time processing accounts service first, then censors
at the horizon, otherwise completes reviews, admits arrivals, and dispatches
in reviewer-ID order after settling due verification and author-response events
(including zero-delay chains, in stable proposal order). Shift-end completions
before the horizon may merge.
Interrupted reviews remain assigned across off-duty gaps. A proposal with no
non-author reviewer having duty after its readiness carries a
`no_eligible_reviewer:<pr_id>` limitation; it is not silently self-reviewed.
Boundary records contain cumulative arrivals, merges, in-progress and unresolved
counts; reviewer accounting separates active seconds from clipped duty seconds.
Internal event arithmetic is exact; public times and durations remain floats.
This is a Python API, not yet a CLI experiment or a reporting artifact contract.

v0.1.0 models a **CI-before-review, one-required-review** workflow with a single
central FIFO queue. It does not reproduce repositories that review in parallel
with CI, require several approvals, route by CODEOWNERS, share review capacity
across repositories, or use a merge queue. It is not an emulation of GitHub
branch protection.

Reopened pull requests and repeated draft/ready lifecycles are excluded from the
mechanistic-fit cohort unless their lifecycle is unambiguous; they remain in
dataset totals with the excluded fraction shown.

## Attribution

A bot account is not an AI coding agent, and a human account can submit
AI-assisted work. `unknown` origin is a valid result, not a value to guess from
pull-request size or writing style. There is no AI-authorship classifier and no
estimate of the fraction of AI-written code. A count of AI-authored pull
requests measures neither business value nor developer productivity.

## Censoring and selection

Pull requests still open at the horizon are right-censored. A
closed-without-merge pull request is a competing outcome, not a missing merge.
Latency summaries are completion-conditioned and are reported together with
fixed-horizon completion shares, unresolved work, abandonment, and queue
metrics — never a scenario ranking by median latency among the few pull requests
that finished.

## Uncertainty

Three kinds of uncertainty stay separate: random workflow variation under fixed
parameters, Monte Carlo estimation error from a finite replication count, and
assumption uncertainty across named assumption sets. Hand-picked low, base, and
high assumption sets are not a probability distribution and not a posterior.
More replications reduce numerical sampling error; they do not make an
unsupported assumption more valid.

## Random streams

`simulation.arrivals.generate_proposals` resamples complete Monday-based local
weeks with replacement and emits FIFO-compatible proposals, retaining each
arrival's author and declared origin together. Callers must supply complete
training weeks in one declared timezone, including empty weeks, and validate
coverage and the training cutoff upstream. Dataset feature extraction is not
implemented by this primitive. Fewer than eight distinct weeks adds
`exploratory_only`; no weeks is an error. This flag must travel with downstream
results and does not certify empirical model readiness when absent.

Offsets are wall-clock durations from Monday midnight, mapped to UTC before
half-open horizon clipping. Ambiguous or nonexistent arrival times in sampled
weeks are rejected, even outside the clipped portion of a sampled week. Source
weeks are sorted by date; arrival tuple positions must remain stable. Proposal
IDs use the target Monday and source tuple position, independent of scenario
ordering and horizon length. Readiness is elapsed seconds from the run start.
Latent service draws remain the downstream caller's responsibility using these
IDs and the keyed stream factory; no observed delay becomes effort.
This is a Python API, not a persisted model or CLI calibration command.

Purpose-keyed streams provide deterministic pseudorandom draws, not a proof of
statistical independence or cryptographic randomness. Reproducibility assumes
the same key encoding, PCG64, NumPy environment, and sampling calls; arbitrary
NumPy upgrades are not a promise of identical distribution samples. Callers
must use stable proposal/revision/purpose identities and omit scenario IDs for
shared latent variables. The factory cannot infer the semantic role of a string.
The FIFO engine keys verification decisions by proposal ID and revision with
purpose `verification`, and requested changes by proposal ID and review visit
with purpose `requested-change`, using the caller's root seed and replication.

## Review bypass

The simulated bypass scenario reduces modeled human-review demand and increases
unreviewed merges. The model does not estimate escaped defects and does not
establish policy safety: `defect_escape_rate`, `security_risk_change`, and
`policy_safety` are `null` with an `unsupported_in_v0_1` reason. Removing review
also removes modeled review-requested changes, so an apparent flow gain is not
an estimate of net engineering benefit. No real GitHub action is ever taken; the
term refers only to the simulation.

## Validation

Implementation verification, historical descriptive validation, and intervention
validation are separate gates. Passing a baseline fit is not causal validation.
v0.1.0 does not establish that simulated policy effects match the outcomes of
actual changes.

## Initialization

Warm-up starts from empty. A warm-up length is a configuration choice, not a
guarantee of steady state, especially under overload. v0.1.0 does not claim a
faithful forecast initialized from a team's exact partially completed reviews.

## Duty calendars

Duty windows are declared availability, not measured active review effort.
The calendar primitive materializes weekly windows and explicit dated absences;
it does not infer working hours or automatically apply regional holidays.
Ambiguous and nonexistent local boundaries are rejected before simulation.
UTC intervals depend on the installed IANA timezone database. See
[calendar semantics](calendars.md) for the exact boundary and warm-up rules.

## Congestion

A load sweep is a set of explicit scenarios. Any threshold crossing is
conditional on the model, horizon, chosen backlog threshold, calendars, and
service assumptions. There is no universal saturation point and no proven phase
transition.

## Privacy

This tool handles potentially sensitive employee and repository metadata even
without source code. Use it only on data you are authorized to analyze.
Pseudonymized data is not necessarily anonymous: small teams and distinctive
activity can still be identifiable. Reports default to repository and cohort
aggregates and provide no individual ranking.
