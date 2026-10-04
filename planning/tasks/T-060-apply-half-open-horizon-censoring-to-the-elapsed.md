---
id: T-060-apply-half-open-horizon-censoring-to-the-elapsed
title: Apply half-open horizon censoring to the elapsed-delay benchmark
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#empirical-model-and-validation
dependencies: []
updated_at: "2026-10-04T21:54:18Z"
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

No implementation changes in this audit. Relevant owner:
`validation.replay_elapsed_delay_benchmark`; review-delay selection uses `<=`
where weekly merge selection already uses `<`, and fixed-horizon successes lack
an explicit in-window completion check. Existing full suite passes (805 tests).
