---
id: T-056-reject-unrepresentable-simulation-calendar-bounds
title: Reject unrepresentable simulation calendar bounds with structured errors
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-04T20:15:18Z"
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

### Implementation and workflow-v3 evidence

- Step 1: `taskrail validate` returned `state valid`; `next --json` selected
  this task with `off_spec: false`, pinned to `specs/v0.1.0.md`. The checkout
  started clean on the specified main base. Inspected local arithmetic, both
  directions of timezone conversion, fixed-offset absences, calendar iteration,
  arrival week iteration, default execution resolution, and staged publication.
- Step 2: added CLI boundary cases before production changes. Running
  `uv run pytest tests/unit/experiment_test.py -k 'unrepresentable_calendar or nearby_calendar' -q`
  produced 18 failed / 1 passed: uncaught `OverflowError`, exit 1 instead of 2,
  and two valid nearby runs failing. After the minimal exception/iteration
  changes, the same selection passed all 19 cases. No requested date is clamped.
- Step 3: ruff, formatting, and mypy passed; experiment plus simulation tests
  passed 381 cases. An existing Tokyo week-boundary test caught a date-only
  iteration stop; using the full local datetime difference restored its
  one-hour arrival and retained partial-Monday semantics.
- Step 4: dedicated Task loaded `code-simplifier`, inspected the task diff and
  surrounding contracts, and made no changes: no behavior-preserving reduction
  was warranted. No suggestions were rejected.
- Step 5: parallel independent Task lanes loaded `code-reviewer`: General
  (`ecc/agents/code-reviewer.md`), Python (`python-reviewer.md` plus
  `python-patterns/REFERENCE.md`), Security (`security-reviewer.md` plus
  `security-review/REFERENCE.md`). Security covers invalid-input and overwrite
  data-loss risks; Python covers datetime arithmetic. Database/framework lanes
  were omitted because no database, schema, concurrency, or framework contract
  changed. This stays within the specialist budget. A fresh candidate-validation
  Task loaded `code-reviewer` and deduplicated the findings below.
- Step 6: the one validated finding was fixed with strict TDD. The new
  calendar and CLI overnight regressions produced 3 failed / 5 passed before
  the fix (overflow and exit 2 instead of 0), then 8 passed after moving the
  both-fold UTC start-overlap check before overnight end-date construction.
- Step 7: `mise run check` passed: ruff, 61 formatted files, mypy's 60 source
  files, all 775 tests, and every commit/push/author/mutation-floor/orb-setup
  guard suite. A fresh disposition-verification Task loaded `code-reviewer`,
  independently passed 8 focused and 89 surrounding tests, and concluded
  "No newly introduced task-relevant findings." One review/fix/recheck cycle.
- Manual subprocess checks: ordinary input exited 0 and published nine files.
  Both original extreme-date reproductions under `--json --overwrite` exited
  2, emitted an error record with empty stderr, and preserved all nine existing
  bundle files byte-for-byte. Unit tests also exercise absent output and nested
  existing output, duty-zone conversion, and fixed-offset absences at both ends.
- Step 8: lifecycle finalization follows all review and verification evidence;
  no second task is implemented. README and Unreleased changelog document the
  invalid-input contract and nearby-date iteration correction.

### Review findings and dispositions

- Python F1 (validated; General F-1 and Security SEC-1 duplicate):
  "A representable run can fail when a configured overnight window starts after
  the run’s exclusive end on the maximum date. The code constructs the following
  local date before checking whether the window overlaps the span."
  Evidence: `simulation/calendars.py` constructed the overnight next date before
  the overlap check. FIXED by checking earliest UTC start against the exclusive
  end first; two unit endpoints include equality, plus end-to-end CLI coverage.
- General F-2: "A representable span near the upper datetime limit can fail
  while converting a sampled arrival later in its final partial week, despite
  that arrival being outside the half-open span." REJECTED by candidate
  validation: `docs/limitations.md` requires UTC mapping and strict DST validation
  before clipping even outside the sampled portion. The proposed local-span
  filtering would violate that contract. Python F2 duplicates this candidate.
- No validated finding is deferred or unresolved. Arrival strict validation
  remains unchanged; unrepresentable sampled boundaries receive the structured
  invalid-input error rather than being silently skipped.

### Verification limitation and follow-up

The stock `BASE=origin/main mise run test:mutate` failed statistics collection
because its scratch project lacked `scripts.run_live_workflow`. A `PYTHONPATH`
workaround also failed. Follow-up T-057 was created using `taskrail task new`
for this pre-existing harness issue, without implementing it. Copying the scripts
into the disposable mutation scratch tree allowed the differential run to pass:
CLI 80/98 (81.6%), arrivals 174/190 (91.6%), calendars 263/293 (89.8%), all above
the per-module floor. The scratch copy was removed afterward. This workaround
is not a claim that the stock mutation command passes. A fresh final
`mise run check` after disposition verification again passed all 775 tests and
every static and shell-policy gate.
- 2026-10-04T20:15:18Z: verification pass
