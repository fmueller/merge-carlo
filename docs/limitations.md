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
