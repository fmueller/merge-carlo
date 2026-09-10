---
id: T-011-review-bypass
title: Simulate audited human review bypass
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#stochastic-scenario-semantics
dependencies:
    - T-009-ai-arrival-transforms
updated_at: "2026-09-10T15:27:23Z"
---

# T-011-review-bypass Simulate audited human review bypass

## Description

Implement the hypothetical bypass scenario: an assumed eligible fraction or an
operator-supplied per-proposal label, an independently keyed audit draw
selecting the declared fraction for normal human review, and non-audited
eligible proposals skipping human review after verification passes. Eligibility
and audit draws are fixed across comparable scenarios. No risk classifier and no
real GitHub action.

## Acceptance

- An eligible fraction of zero reproduces baseline semantics under common random numbers.
- An eligible fraction of one with an audit fraction of zero consumes no human review for eligible work; only verification and coordination delay merges.
- Eligible count, audited count, merges without human review, their share of merges, and modeled review effort avoided are all reported.
- `defect_escape_rate`, `security_risk_change`, and `policy_safety` are `null` with an `unsupported_in_v0_1` reason.
- A bypassed pull request never counts as human-reviewed in a review service-level metric.

## Verification Notes

- Deterministic fixtures at both fraction extremes.
- A report test asserting the required qualification text and the null risk fields.

## Implementation Notes

Implemented the v0.1.0 Python API slice in `simulation.engine` and
`simulation.bypass`. Eligibility/audit are assumed probabilities, not quotas;
`eligible_fraction=None` consumes operator labels. Explicit bypass configuration
is required. Coordination delays both reviewed and bypassed merges without
occupying reviewers. Avoided effort is one assumed rounded service visit per
bypass transition, including later censored/abandoned work, not a counterfactual
baseline saving. Whole-run diagnostics are not measurement-window SLA metrics;
bypasses carry no human-review timestamp, approval, visit or active service.
T-012/T-013/T-014 already own runner, measurement-window and artifact integration.

### Workflow-v3 evidence

1. Understand: `taskrail validate` passed; `taskrail next --json` selected this
   task at the requested base `1cc914f`. Read the active spec, task, domain,
   engine, capacity conventions and downstream reporting tasks. No scope change.
2. Strict TDD: `uv run pytest tests/unit/simulation/bypass_test.py -q` first
   failed with missing `merge_carlo.simulation.bypass`; implementation made all
   15 original tests pass. Fixtures exercise fractions zero/one, labels, audits,
   keyed pairing, verification, coordination, abandonment/horizon ties and null
   risk fields without human-review evidence.
3. Initial checks: ruff and mypy passed; full pytest passed 284 tests.
4. Dedicated Task loaded `code-simplifier`; accepted removal of redundant bool
   conversions and mutable effort counter, deriving effort from bypass flags.
   Post-simplification engine/bypass tests: 97 passed; full suite: 284 passed.
5. Independent parallel read-only Tasks loaded `code-reviewer`: General used
   ECC code-reviewer; Python used ECC python-reviewer and python-patterns.
   Both concluded verbatim: "No concrete task-relevant findings."
   General is mandatory and Python covers changed source; Security, Database,
   frameworks, ML and other domain lanes omitted because no trust boundary,
   persistence, framework or external-system change is present. A fresh
   candidate-validation Task loaded the skill and confirmed an empty candidate
   set; no rejected or deduplicated candidates.
6. No reviewer findings to fix or defer. Self-verification found weak report
   coverage (initial bypass mutation efficacy 34/55, 61.8%). Added an asymmetric
   one-unreviewed/three-merged/four-arrival golden report test. Deliberately
   changing the denominator to all arrivals failed with `0.25 != 1/3`; restored
   implementation passed. Added missing reviewer-limitations assertions for
   disabled bypass, labeled work and full audit without reviewers. Deliberate
   AND-to-OR regression failed on missing `no_eligible_reviewer:a`; restored
   implementation passed. No mutation exclusions or floor changes.
7. Final `mise run check`: ruff, format, strict mypy, all 285 pytest tests and
   all commit/push/author/mutation-floor/orb-setup guard suites passed. Targeted
   bypass suite: 16 passed. Fresh read-only `code-reviewer` disposition verifier
   confirmed "No concrete task-relevant findings." One review/disposition cycle,
   no unresolved or deferred findings. Its Taskrail PATH limitation was resolved
   by the parent using `mise exec -- taskrail`; validation/status passed.
8. Taskrail verification/completion follows these gates. Only this task was
   implemented; no new follow-up task was needed. Existing T-033 applies to
   v0.1.0 mutation discovery of decorated dataclass methods.

### Final mutation and manual evidence

`BASE=1cc914f4c45f87d39a433e42c2d764bd2e8e32d3 mise run test:mutate`
passed the unchanged scoped 80% per-module floor. Raw statuses from
`uv run mutmut results --all true`:

- bypass: 55 total, 53 killed, 2 survived, 0 timeout; 53/55 = 96.4%.
- engine: 553 total, 536 killed, 14 survived, 3 timeout; the repository policy
  counts timeouts as detected, giving 539/553 = 97.5%. Raw killed-only efficacy
  is 536/553 = 96.9%. No selected mutants were unexecuted.
- Bypass survivors are diagnostic wording and AND-to-OR on review evidence
  (equivalent on fresh engine runs: bypassed merges have zero review visits).
  Engine survivors include diagnostic wording, redundant horizon boundaries,
  unused initial previous-time values, and exact random-threshold equality.
  These remain raw and unsuppressed; scores do not claim exhaustive coverage.
  Decorated dataclass methods remain subject to existing T-033's discovery gap.

Manual Python API fixture: six synthetic arrivals, one reviewer, verification
2s, service 10s, coordination 3s, seed 19, eligibility 1, audit 0.5. The rendered
report gave 6 eligible, 4 audited, 2 unreviewed merges, share 1/3, and 20 assumed
review seconds avoided. Assertions checked audited service and absence of
human-review timestamps on bypassed work. All three unsupported risk fields
were null with reasons, and the report included policy-safety/net-benefit
qualifications. No network, real dataset or GitHub write was involved.
- 2026-09-10T15:27:23Z: verification pass
