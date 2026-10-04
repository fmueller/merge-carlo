---
id: T-055-reject-excessively-nested-configuration-inputs
title: Reject excessively nested configuration inputs with structured errors
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-04T19:41:56Z"
---

# T-055-reject-excessively-nested-configuration-inputs Reject excessively nested configuration inputs with structured errors

## Description

Audit cycle 1 confirmed that small but deeply nested YAML configuration and JSON
artifact inputs escape the CLI's structured error handling. Release Hardening
requires invalid inputs to return exit 2 and supports machine-readable errors;
an input exceeding parser depth is invalid input, not an internal crash.

Normalize parser-depth failures at the relevant input boundaries without relaxing
safe YAML loading, size budgets, schema checks, or finite-number validation.

## Acceptance

- Deeply nested scenario YAML and model/validation JSON return exit 2, with a
  JSON error record under `--json`, no traceback, and no successful output bundle.
- Normal valid inputs still succeed; unknown fields, unsafe YAML tags, malformed
  encodings and existing size limits remain rejected.
- Regression tests exercise actual CLI entry points as well as shared loaders;
  inputs must exceed runtime parser depth while remaining below byte budgets.

## Verification Notes

Confirmed on main revision `1cc5d3baec996432adb623c6058510d9f1a35bd7` after
fetching origin/main. Synthetic local reproduction from repository root:

```bash
mkdir -p /tmp/mc-depth-repro
uv run python - <<'PY'
from pathlib import Path
from tests.unit.experiment_test import write_model, write_scenarios
p = Path('/tmp/mc-depth-repro')
write_model(p / 'model.json')
write_scenarios(p / 'scenarios.yaml')
(p / 'deep.yaml').write_text('schema_version: 1\nscenarios: ' + '[' * 2000 + '0' + ']' * 2000)
(p / 'deep.json').write_text('[' * 20000 + '0' + ']' * 20000)
PY
uv run merge-carlo --json simulate --model /tmp/mc-depth-repro/model.json \
  --scenarios /tmp/mc-depth-repro/deep.yaml --out /tmp/mc-depth-repro/yaml-out
uv run merge-carlo --json simulate --model /tmp/mc-depth-repro/deep.json \
  --scenarios /tmp/mc-depth-repro/scenarios.yaml --out /tmp/mc-depth-repro/json-out
uv run merge-carlo --json validate --input /tmp/mc-depth-repro/deep.json \
  --out /tmp/mc-depth-repro/validation-out
```

Observed: each command exits 1 with an uncaught `RecursionError` and traceback
instead of a JSON diagnostic. YAML is about 4 KiB and JSON about 40 KiB, below
their configured limits. Expected independently from spec: exit 2 and structured
invalid-input output. A 2,000-level JSON array was rejected normally; 20,000
levels distinguishes the uncaught failure. Unsafe object-construction YAML and
invalid UTF-8 were correctly rejected with exit 2.

## Implementation Notes

No implementation change in this audit. Relevant boundaries include
`configuration._load_config`, `experiment._read_json`, and
`validation.load_validation_evidence`. Do not preserve raw adversarial payloads
or full tracebacks in task evidence.

### Implementation and workflow-v3 evidence

- Confirmed clean base and pinned `specs/v0.1.0.md`; `taskrail validate` and
  `taskrail next --json` selected T-055 before start and again before finalization.
  Invoke Taskrail through `mise exec -- taskrail` in this orb.
- Strict TDD: `uv run pytest tests/unit/input_depth_test.py --tb=line -q`
  failed all 10 cases before implementation: four loader RecursionErrors and six
  CLI exit-code assertions (1 instead of 2). After adding RecursionError to the
  existing three boundary catches, all 10 passed. No parser, schema, size,
  encoding, finite-value, or YAML safety rules changed.
- Initial focused checks: input_depth, configuration, experiment, validation,
  and cli unit test files: 144 passed; Ruff and mypy passed.
- Dedicated Task loaded code-simplifier: no changes recommended; 10 tests passed.
- Parallel independent Tasks loaded code-reviewer: General with common review
  checklist, Security with security-review and common security rules, Python
  with python-patterns. All returned: "No concrete task-relevant findings."
  These lanes cover correctness, input trust boundaries, and Python exception
  semantics. Database/framework/domain lanes omitted because untouched.
- Fresh candidate-validation Task: zero candidates, rejected IDs, or duplicates;
  "No concrete task-relevant findings." No fixes, deferrals, or follow-ups.
- Fresh disposition-verification Task confirmed the empty disposition set and
  returned "No concrete task-relevant findings." One review cycle, no issues.
- Manual installed-CLI subprocess checks of all three confirmed reproductions:
  exit 2, exact structured JSON diagnostic, empty stderr, output directory absent.
  Temporary inputs were discarded; no raw payloads or tracebacks retained.
- Final `mise run check`: Ruff passed; 61 files formatted; mypy passed on 60
  source files; pytest 751 passed; commit-message, push-message, author,
  mutation-floor/differential-guard, and orb-setup guard suites passed.
  Mutation execution was not needed for three exception-tuple additions;
  strict red/green tests directly demonstrate the changed failure behavior.
- 2026-10-04T19:41:56Z: verification pass
