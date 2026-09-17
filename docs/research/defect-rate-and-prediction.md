# Defect rate and defect prediction

## Main conclusion

Lines of code are useful as an exposure or normalization factor, but they are
not a sufficient causal explanation for defects. The more defensible model uses
size together with relative churn, change history, complexity, task type,
testing and review evidence, and repository-specific baselines.

An observed defect rate is also not automatically an introduction rate. It is
affected by test coverage, review effort, reporting practices, severity
thresholds, deployment exposure, and the observation window.

## Evidence

### Relative churn is more useful than raw size alone

[Nagappan and Ball (ICSE 2005)](https://doi.org/10.1145/1062455.1062514)
studied Windows Server 2003 and compared absolute and relative code-churn
measures. Their abstract reports that absolute churn was a poor predictor while
relative measures incorporating component size and the temporal extent of
change were highly predictive; the metric suite discriminated fault-prone from
non-fault-prone binaries with 89% accuracy in that case study.

The result is useful evidence for including changed-code size and normalized
churn. It is not a universal accuracy promise: the data came from one very
large industrial system, and the authors explicitly discuss external-validity
limits.

### Defect-prediction evidence has dataset and validation problems

[Pachouly et al. (2022)](https://doi.org/10.1016/j.engappai.2022.104773)
reviewed 146 software-defect-prediction studies. Their review describes
inconsistent datasets, sparse or insufficient defect labels, and limited
cross-project evidence. This matters for merge-carlo because a model can look
accurate on a public benchmark while learning project-specific measurement
habits rather than a portable defect mechanism.

[He et al. (2015)](https://doi.org/10.1016/j.infsof.2014.11.006)
studied whether a small set of software metrics could perform acceptably
against more complex predictors. The paper is relevant as a counterweight to
feature accumulation: a larger metric set is not automatically a more valid
model, especially when feature acquisition and generalization are weak.

## Measurement distinctions for merge-carlo

The v0.2.0 contract should keep these observations separate:

| Signal | What it can support | What it cannot establish alone |
| --- | --- | --- |
| Pre-merge test or CI failure | A failed verification event and possible merge delay | A production defect or escaped bug |
| Static-analysis finding | A quality-risk proxy | A confirmed functional or security defect |
| Confirmed defect linked to a PR | A defect-incidence observation | The PR was the only cause |
| Production regression or incident | A post-merge outcome with an observation window | Complete defect coverage |
| Revert | An operational rollback signal | That the reverted change was defective |
| Remediation change | Follow-up demand and rework | The original change's exact defect count |

The denominator and linkage basis must travel with every rate. For example,
“issues per KLOC” is different from “confirmed escaped defects per merged PR,”
and neither should be pooled across repositories without accounting for
different detection and reporting processes.

## Modeling implications

The literature supports the following order of work:

1. Define a versioned quality-outcome contract and conservative PR-to-outcome
   linkage.
2. Report descriptive rates with exposure, observation window, missingness,
   and censoring visible.
3. Use temporal holdouts and repository-level or hierarchical effects before
   fitting a latent defect model.
4. Treat counts as potentially sparse and overdispersed rather than assuming
   one independent identical risk per line.
5. Keep static-analysis proxies, confirmed defects, incidents, reverts, and
   remediation demand available as separate metrics.

These points are reflected in the [v0.2.0 quality-adjusted workflow
specification](../../specs/v0.2.0.md).
