---
id: T-059-use-completed-review-evidence-in-held-out
title: Use completed review evidence in held-out validation metrics
status: completed
priority: high
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies: []
updated_at: "2026-10-04T21:34:33Z"
---

# T-059-use-completed-review-evidence-in-held-out Use completed review evidence in held-out validation metrics

## Description

Audit cycle 2 confirmed that held-out replay treats the engine's
`first_review_at` (review start) as a completed substantive review. It uses that
timestamp for reviewed-within-48-hours successes, completion counts, and elapsed
review latency. Consequently, a review still in progress at the horizon is
counted as completed, and a 49-hour review appears reviewed within 48 hours.

Empirical Model And Validation defines observed first substantive review by
submitted approval/changes-requested evidence and requires completion-conditioned
first-review elapsed comparisons. Align replay outcomes with that observable
event. Do not change the separately documented operational queue/start-latency
metric merely to make these validation comparisons agree.

## Acceptance

- Count reviewed-within-48-hours successes only when the first substantive human
  review completes by its deadline; starting service is not success.
- Completion-conditioned validation latency measures readiness to the first
  completed substantive review, matching the observed feature and benchmark
  meanings. Unfinished first visits supply neither a completion nor a zero sample.
- With one arrival, continuous duty, 49-hour service, no loops or coordination,
  replay reports zero 48-hour successes, one first-review completion with latency
  176400 seconds, and one seven-day merge. Matching observed outcomes pass strict
  validation rather than incorrectly failing review-share and latency gates.
- With 40-day service and only 30 days remaining after readiness, report zero
  completed first reviews and undefined latency; enforce the insufficient-evidence
  gate instead of fabricating usable review evidence.
- Exercise service spanning off-duty intervals, requested-change first decisions,
  and completion/deadline/horizon boundaries using independently derived expected
  outcomes. Preserve no-self-review and no stale-revision approval semantics.

## Verification Notes

Confirmed on fetched main `324feb5802363f3e37b0b25b0199a6c58ab90b01`.
Reproduce from repository root with synthetic, offline replay data:

```bash
mkdir -p /tmp/mc-review-repro
uv run python - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from pydantic import TypeAdapter
from tests.unit.validation_test import replay_input
from merge_carlo.validation import (
    FrozenReplayModel, ObservedOutcomes, ValidationInput, replay_held_out,
)
p = Path('/tmp/mc-review-repro')
request = replace(
    replay_input(),
    model=FrozenReplayModel('fifo-v0.1', 'UTC', 49 * 3600),
    observed=ObservedOutcomes(0, 1, 1, 1, (176400.0,), (1, 0, 0, 0, 0), 0),
)
for label, item in [
    ('49-hours', request),
    ('unfinished', replace(request, model=FrozenReplayModel('fifo-v0.1', 'UTC', 40 * 86400))),
]:
    print(label, replay_held_out(item).replay_replications[0])
    payload = TypeAdapter(ValidationInput).dump_python(item, mode='json')
    payload['schema_version'] = 1
    (p / (label + '.json')).write_text(json.dumps(payload))
PY
uv run merge-carlo --json validate --input /tmp/mc-review-repro/49-hours.json \
  --out /tmp/mc-review-repro/validation --strict
```

The fixture has one PR ready January 2, continuous non-author reviewer duty,
and a January 1 through February 1 half-open replay span. Three deterministic
replications use the same constant service assumptions.

Independent calculation: 49 hours of uninterrupted service completes January 4
at 01:00 UTC, after the 48-hour deadline and before seven days. The observed
outcomes above exactly match that schedule. Actual replay instead reports
`reviewed_within_48_hours_successes=1`, `first_review_median_seconds=0.0`, and
`first_review_completions=1`. The CLI exits 4, with absolute errors 1.0 on review
share and 176400 seconds on review latency; merge, weekly-count and backlog
gates pass. Expected strict result: pass/exit 0.

The 40-day variant cannot finish before February 1, but actual replay still
reports the same review success, zero latency, and one completion. Independently
expected: zero review completions, zero reviewed-within-48-hours successes, and
undefined completion-conditioned latency. This rules out mere rounding or an
intentional latency-only display convention as the cause.

## Implementation Notes

No fixes made in this audit. Relevant owner: `validation.replay_held_out`.
The engine records `first_review_at` on REVIEW_STARTED. Capture actual first
decision completion evidence rather than inferring it from merge time (later
coordination and repeated reviews can differ). The current full suite passes
(775 tests); some validation tests use synthetic FIFO results whose assertions
encode start-time accounting, so review those expectations against the spec.

### Implementation cycle evidence

- Source guard: `taskrail validate` reported `state valid`; `taskrail next
  --json` selected exactly T-059 on clean main at the supplied base. Active spec
  remained `specs/v0.1.0.md`. Only this task was started.
- Lifecycle accounting now retains the first approval or changes-requested
  completion separately from `first_review_at`. Replay consumes completion;
  operational start/queue metrics and engine ordering remain unchanged. The
  internal timestamp is excluded from v1 experiment traces; the unchanged
  golden bundle verifies contract compatibility.
- Strict TDD: the eight new replay cases initially failed (zero start latency,
  false 48-hour successes, and strict exit 4); all eight passed after the minimal
  completion-accounting change. The lifecycle assertion first failed with
  `AttributeError`, then passed. Four timestamp-contract cases failed with
  `DID NOT RAISE`, then passed after matching existing time validation.
- Independent expected values cover 48-hour inclusive deadlines, one second
  before and exactly at the half-open horizon, 49-hour service, 40-day unfinished
  service, and a requested-change first decision spanning off-duty time followed
  by a later approval and merge. Replay reproductions now report 49h:
  successes=0, completions=1, latency=176400, seven-day merges=1, validation=pass;
  40d: successes=0, completions=0, latency=None, validation=insufficient_evidence.
- Two dedicated `code-simplifier` Task passes made no changes. Review lanes were
  General and Python, each in separate parallel read-only `code-reviewer` Tasks.
  Security, database and framework lanes were omitted because no trust boundary,
  SQL, schema migration or framework behavior changed. The trace compatibility
  fix received a second review cycle; both final lanes reported exactly
  "No concrete task-relevant findings."
- A fresh candidate-validation Task validated C1, verbatim: "Reject a
  completed-review timestamp that predates the first review start, or is present
  without a first review start." Disposition: fixed. Two regression cases failed
  with `DID NOT RAISE`, then passed with the chronology guard; equality remains
  accepted. No candidates were rejected or deferred. A second fresh candidate
  validator confirmed no new candidates; a fresh disposition-verification Task
  confirmed C1 resolved and reported "No concrete task-relevant findings."
- Initial checks: Ruff/mypy passed; validation plus simulation passed 434 tests.
  After disposition, validation/domain passed 220 and validation/domain/artifacts
  passed 242. The full gate first found formatting (corrected with Ruff) and then
  the trace golden regression (fixed without modifying the fixture). Final
  `mise run check` passed: 788 tests, Ruff, 61 formatted files, strict mypy over
  60 source files, and all commit/push/author/mutation-floor/orb-setup shell suites.
  The first mutation attempt stopped on that same golden regression; the final
  differential run includes artifacts, domain, and validation, without changing
  the floor or suppressing mutants.
- Final differential mutation command: `BASE=855a593f14a48170e2ade188dca2e87687e57f23
  mise run test:mutate`, exit 0. Per-module floor results: artifacts 650/798
  (81.5%), domain 268/367 (73.0%), validation 1212/1517 (79.9%), all above 70%.
  These are module-level efficacy results, not a claim that every mutant was
  killed. No new task-relevant follow-up was identified.
- 2026-10-04T21:34:33Z: verification pass
- 2026-10-04T21:34:33Z: Completed substantive first-review accounting with operational start metrics and v1 artifacts preserved; reviewed and fully verified.
