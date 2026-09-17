# Non-Blocking Continuous Reviews

This note records ideas from Thierry de Pauw's [case-study
article](https://thinkinglabs.io/articles/2023/05/02/non-blocking-continuous-code-reviews-a-case-study.html)
and [slide deck](https://thinkinglabs.io/talks/2024/02/06/non-blocking-continuous-code-reviews-a-case-study.html).
It is inspiration for a future merge-carlo workflow model, not evidence that the
practice is effective for every team or repository.

## Case-study idea

The team used trunk-based development and reviewed changes on mainline after
they were merged. Automated tests, exploratory testing, and static analysis
protected delivery; human review supplied learning, knowledge sharing,
readability and design feedback. Every change was still expected to receive a
review, and findings were picked up immediately, but waiting for a reviewer did
not stop delivery.

The deck presents the resulting trade-off as a flow problem:

- pull-request review creates transaction cost and delay;
- waiting encourages larger batches and more work in progress;
- smaller increments and continuous feedback support flow and refactoring;
- pairing or ensemble programming remains a stronger option when practical;
- regulated work may require a blocking or paired approach instead.

The case study does **not** establish that unreviewed code is safe, that review
findings are defects, or that non-blocking review is a universal policy. Its
claims are a process hypothesis to test under explicit assumptions.

## Implications for merge-carlo

The relevant comparison is not “review versus no review.” It is:

```text
blocking review:       verify -> human review -> deliver
non-blocking review:   verify -> deliver -> human review -> follow-up work
```

The existing hypothetical bypass scenario is therefore not a faithful model of
this practice: bypassed work receives no later review. A future implementation
should keep delivery and feedback as separate lifecycles. A delivered pull
request must remain terminal; a post-delivery review should be a separate review
item associated with that delivery rather than a transition that reopens it.

The useful question is:

> Under declared review-capacity and remediation assumptions, does moving human
> review after verified delivery reduce delivery delay while keeping review
> debt and follow-up work bounded?

This framing keeps the model focused on system flow. It does not turn merge-carlo
into a productivity estimator or a safety-certification tool.

## Candidate experiments

An eventual scenario suite could compare:

1. the current blocking-review baseline;
2. continuous post-delivery review;
3. a daily review batch with a declared review window;
4. post-delivery review with reviewer absence or increased demand;
5. a mixed policy where audited work remains blocking and ordinary work is
   non-blocking; and
6. immediate-priority remediation of review findings.

The report should show delivery latency separately from feedback latency, along
with review-debt size and age, reviewer utilization, requested-change/finding
counts, follow-up work, and audited-work compliance. It must not call findings
defects or infer escaped defects, security risk, business value, or individual
performance.

The article's rule to review before starting new work is also important, but it
requires a model of work initiation, coding capacity, and work in progress. The
current simulator begins at `ready_for_review` and deliberately excludes those
quantities. Until that boundary is explicitly extended, the rule should remain a
declared qualitative operating assumption rather than an invented metric.

## Evidence and limits

A future model needs explicit delivery and review timestamps, including
post-delivery reviews and any follow-up linkage. Direct-mainline commits and
feature-level grouping may require collection contracts beyond the current
pull-request-centric data. Active review effort must remain an explicit assumed
quantity; elapsed delivery or feedback delay must not be reused as service time.

Validation should include hand-calculated fixtures for delivery continuing while
review capacity is unavailable, review debt accumulating and later draining,
post-delivery findings not reviving a merged delivery, and audited work retaining
its blocking gate. Historical replay can be descriptive, but it cannot establish
that the intervention causes better quality or flow.
