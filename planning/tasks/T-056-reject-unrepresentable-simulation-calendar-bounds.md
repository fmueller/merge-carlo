---
id: T-056-reject-unrepresentable-simulation-calendar-bounds
title: Reject unrepresentable simulation calendar bounds with structured errors
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-04T19:25:53Z"
---

# T-056-reject-unrepresentable-simulation-calendar-bounds Reject unrepresentable simulation calendar bounds with structured errors

## Description

Audit cycle 1 confirmed that accepted execution dates can overflow when the
simulator adds the horizon or subtracts warm-up. Release Hardening requires
invalid inputs to return exit 2 with structured errors. A requested run outside
the supported datetime range must be rejected, not produce an internal crash.

## Acceptance

- `simulate` rejects dates whose local horizon/warm-up or UTC conversion cannot
  be represented, returning exit 2 and a JSON error record under `--json`.
- No traceback or successful result bundle is emitted; failed overwrite leaves
  an existing bundle unchanged.
- Exercise both upper and lower date limits and valid nearby dates. Preserve
  ordinary DST, timezone, and half-open calendar semantics without clamping dates.

## Verification Notes

Confirmed on main revision `1cc5d3baec996432adb623c6058510d9f1a35bd7` after
fetching origin/main. Synthetic reproduction from repository root:

```bash
mkdir -p /tmp/mc-date-repro
uv run python - <<'PY'
from pathlib import Path
from tests.unit.experiment_test import write_model, write_scenarios
p = Path('/tmp/mc-date-repro')
write_model(p / 'model.json')
write_scenarios(p / 'scenarios.yaml')
original = (p / 'scenarios.yaml').read_text()
for year, stamp in [('9999', '9999-12-31T00:00:00'), ('0001', '0001-01-01T00:00:00')]:
    (p / (year + '.yaml')).write_text(original.replace('2026-09-08T00:00:00', stamp))
PY
uv run merge-carlo --json simulate --model /tmp/mc-date-repro/model.json \
  --scenarios /tmp/mc-date-repro/9999.yaml --out /tmp/mc-date-repro/upper-out
uv run merge-carlo --json simulate --model /tmp/mc-date-repro/model.json \
  --scenarios /tmp/mc-date-repro/0001.yaml --out /tmp/mc-date-repro/lower-out
```

Observed for both inputs: exit 1, uncaught `OverflowError: date value out of
range`, and no JSON diagnostic. Upper bound was also reproduced in a separate
CLI process. Expected independently: year 9999 plus one day and year 0001 minus
one warm-up day are unrepresentable; reject as invalid input with exit 2.
The unchanged September 2026 fixture succeeds with exit 0.

## Implementation Notes

No implementation change in this audit. `simulation.calendars.materialize_run_bounds`
adds/subtracts calendar days without translating overflow to a domain error;
`cli.simulate` catches OSError/ValueError but not OverflowError. Check adjacent
calendar conversion/materialization paths rather than special-casing the two
reproduction dates.
