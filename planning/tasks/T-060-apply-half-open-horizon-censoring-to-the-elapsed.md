---
id: T-060-apply-half-open-horizon-censoring-to-the-elapsed
title: Apply half-open horizon censoring to the elapsed-delay benchmark
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies: []
updated_at: "2026-10-04T22:11:28Z"
---

# T-060-apply-half-open-horizon-censoring-to-the-elapsed Apply half-open horizon censoring to the elapsed-delay benchmark

## Description

Audit cycle 3 confirmed that the elapsed-delay benchmark counts a first-review
completion exactly at the excluded replay horizon, including its latency sample.
When that instant is also the 48-hour or seven-day deadline, it can report a
reviewed/merged success that the FIFO replay correctly censors. Its weekly merge
counts already exclude the same horizon merge, creating inconsistent outcomes
within the reference benchmark.

The active spec requires the benchmark to apply the same cohort and horizon
accounting as mechanistic replay. `docs/validation.md` declares half-open bounds;
`docs/limitations.md` explicitly censors completion at the horizon. This is
distinct from T-059's review-start-versus-completion bug: the new defect is in
reference benchmark censoring, and T-059's original cases now pass.

## Acceptance

- Exclude benchmark first-review completions and latency samples at or beyond the
  replay end; no censored review or merge becomes a fixed-horizon success.
- Keep benchmark and FIFO cohort/horizon accounting consistent. For identical
  deterministic event schedules their review/merge outcomes agree, including
  exact horizon/deadline ties; undefined outcomes must not become favorable zeros.
- Exercise one second before, exactly at, and one second after the half-open end
  for both review and merge completion, through replay and persisted CLI output.
- Preserve inclusive service-level deadlines when they lie strictly inside the
  observation interval, weekly merge counts, and the descriptive-only benchmark
  limitation. Do not change source completion-category metadata into a claim of
  simulated in-window completion.

## Verification Notes

Confirmed on fetched main `ab38ff525b072622d35d6c7a580dabc470121ea7`.
Synthetic reproduction from repository root:

```bash
mkdir -p /tmp/mc-benchmark-repro
uv run python - <<'PY'
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from pydantic import TypeAdapter
from tests.unit.validation_test import replay_input
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.validation import (
    ElapsedDelayObservation, FrozenReplayModel, ReplayArrival,
    ValidationInput, replay_held_out,
)
p = Path('/tmp/mc-benchmark-repro')
for days in (2, 7):
    delay = days * 86400
    request = replace(
        replay_input(),
        model=FrozenReplayModel('fifo-v0.1', 'UTC', delay),
        arrivals=(ReplayArrival('p', 'author', WorkOrigin.HUMAN,
            datetime(2026, 1, 32 - days, tzinfo=UTC)),),
        benchmark_observations=(ElapsedDelayObservation(
            datetime(2025, 10, 1, tzinfo=UTC), datetime(2025, 10, 15, tzinfo=UTC),
            delay, 'merged', delay),),
    )
    evidence = replay_held_out(request)
    print(days, evidence.replay_replications[0],
          evidence.delay_benchmark.replications[0].outcomes)
    payload = TypeAdapter(ValidationInput).dump_python(request, mode='json')
    payload['schema_version'] = 1
    (p / f'{days}.json').write_text(json.dumps(payload))
PY
uv run merge-carlo --json validate --input /tmp/mc-benchmark-repro/2.json \
  --out /tmp/mc-benchmark-repro/out-2 --strict
uv run merge-carlo --json validate --input /tmp/mc-benchmark-repro/7.json \
  --out /tmp/mc-benchmark-repro/out-7 --strict
```

The replay ends February 1 at 00:00 UTC. Both constant FIFO service and the
singleton benchmark record put review/merge at exactly that excluded instant.
Independent expected event accounting: zero completed first reviews, no latency
sample, zero in-window merges, and no fixed-horizon success for that event.

Observed in all three replications and persisted `validation.json`:

- January 30 readiness plus 172800 seconds: benchmark reviewed share 1.0 and
  review median 172800; FIFO reviewed share 0.0 and undefined review median.
- January 25 readiness plus 604800 seconds: benchmark merged share 1.0 and
  review median 604800; FIFO merged share 0.0 and undefined review median.
  Both record zero weekly merges, contradicting the benchmark's merge success.
- Both CLI commands correctly exit 0 with `insufficient_evidence`; the defect
  is the persisted benchmark outcomes, not the strict exit policy.
- Control runs with delays one second below/above each value agree between FIFO
  and benchmark. The discrepancy is isolated to exact end equality.

## Implementation Notes

Implemented in `validation.replay_elapsed_delay_benchmark`: review-delay samples
and both fixed-horizon successes require completion strictly before replay end.
Mature-cohort boundaries and inclusive service-level deadlines are unchanged.
Weekly merge accounting, source-category counts, contracts, and the descriptive
reference limitation are preserved. Public validation docs and the existing
unreleased validation changelog entry explain the corrected accounting.

### Workflow-v3 evidence

- Source guard: clean local main at `ac21ef2e4303a15b4c0bdffbc876d7567586c5fe`;
  `mise exec -- taskrail validate` returned `state valid`, and
  `mise exec -- taskrail next --json` selected exactly this task, on pinned
  `specs/v0.1.0.md`, before `taskrail start`.
- Strict TDD: `uv run pytest tests/unit/validation_test.py -k
  'half_open_completions or mechanistic_horizon_boundaries' -q --tb=short`
  returned **3 failed, 10 passed** before production changes. The failures were
  the two exact-end review/merge cases and the original combined-boundary case.
  FIFO already matched independently derived expected event accounting.
- Twelve deterministic cases separately place review and merge one second
  before, exactly at, and one second after the end, with interior-deadline
  controls. All three replications match full expected FIFO/benchmark outcomes.
  Each case executes `--json validate --strict` and checks persisted metrics,
  undefined values/reasons, source categories, and descriptive-only metadata.
  The fixture deliberately requires four replications but supplies three, so
  all CLI cases retain exit 0 / `insufficient_evidence` independently of gates.
- Initial and post-simplification checks:
  `uv run pytest tests/unit/validation_test.py tests/unit/cli_test.py -q`
  returned **118 passed**; Ruff, format checks, and mypy passed.
- Dedicated Task loaded `code-simplifier`; accepted only explicit readiness
  dates in the regression fixture. Production checks needed no abstraction.
- Separate parallel read-only General and Python Tasks loaded `code-reviewer`,
  dedicated lane references, and the Python patterns companion. Both reported
  verbatim: **"No concrete task-relevant findings."** Security and Database
  lanes were omitted because no trust boundary, SQL, schema, or persistence
  mechanism changed. No framework/domain-specialist trigger applied.
- Fresh candidate-validation Task loaded `code-reviewer` and validated the empty
  candidate set: **"No concrete task-relevant findings."** No candidate IDs,
  rejected findings, fixes, deferrals, or follow-ups exist.
- Final `mise run check` passed: **817 tests**, Ruff, format, mypy (60 source
  files), and all commit/push/author/mutation-floor/orb-setup guard suites.
- `BASE=ac21ef2e4303a15b4c0bdffbc876d7567586c5fe mise run test:mutate`
  passed the scoped validation-module gate: **1236/1523, 81.2%, ok**.
  Mutmut reported 1235 killed, one timeout, and 287 surviving mutants; this
  satisfies the module floor, not a claim of complete mutation coverage.
- Fresh disposition-verification Task loaded `code-reviewer`, inspected the
  final diff, independently ran the 13 focused tests and `git diff --check`,
  and concluded: **"No concrete task-relevant findings."** One review cycle;
  no unresolved dispositions or newly introduced task-local issues.
- 2026-10-04T22:11:28Z: verification pass
- 2026-10-04T22:11:28Z: Implemented and independently reviewed half-open horizon censoring; verification passed.
