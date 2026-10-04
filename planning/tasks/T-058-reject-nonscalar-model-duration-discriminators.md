---
id: T-058-reject-nonscalar-model-duration-discriminators
title: Reject nonscalar model duration discriminators without crashing
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-04T21:47:44Z"
---

# T-058-reject-nonscalar-model-duration-discriminators Reject nonscalar model duration discriminators without crashing

## Description

Audit cycle 2 confirmed that a small, shallow model JSON with an array or object
in `parameters[0].value_specification.kind` crashes `simulate`. The model shape
reader tests this untrusted value for membership in a set before validating its
type. Release Hardening requires strict configuration validation and invalid-input
exit 2, not an uncaught TypeError and exit 1. This is distinct from T-055 parser
depth and T-056 calendar arithmetic, whose original reproductions now pass.

## Acceptance

- Array/object duration discriminators return exit 2 and a structured JSON error
  under `--json`, without traceback or a published output bundle.
- Validate discriminator types before hash-based dispatch; preserve rejection of
  other invalid kinds and acceptance of constant/lognormal/empirical durations.
- Cover both array and object inputs through the model loader and CLI, including
  failure with an existing output bundle and explicit overwrite.

## Verification Notes

Confirmed on fetched main `324feb5802363f3e37b0b25b0199a6c58ab90b01`.
Reproduce from repository root with only synthetic fixtures:

```bash
mkdir -p /tmp/mc-kind-repro
uv run python - <<'PY'
import json
from pathlib import Path
from tests.unit.experiment_test import write_model, write_scenarios
p = Path('/tmp/mc-kind-repro')
write_model(p / 'model.json')
write_scenarios(p / 'scenarios.yaml')
model = json.loads((p / 'model.json').read_text())
model['parameters'][0]['value_specification']['kind'] = []
(p / 'model.json').write_text(json.dumps(model))
PY
uv run merge-carlo --json simulate --model /tmp/mc-kind-repro/model.json \
  --scenarios /tmp/mc-kind-repro/scenarios.yaml --out /tmp/mc-kind-repro/out
```

Observed in a separate CLI process: exit 1 and `TypeError: unhashable type:
'list'`, with a traceback rather than JSON output. Replacing `[]` with `{}`
also produced exit 1/TypeError in the CLI harness. Independently expected from
the spec: both are invalid duration kinds and must produce exit 2. Controls
`null`, `true`, `12`, and an unsupported string correctly returned exit 2;
the unmodified model succeeded.

## Implementation Notes

No fixes made in this audit. Relevant owner: `experiment._validate_model_shape`.
The full existing suite passed (775 tests) despite these reproduced failures.

### Completed task cycle

- Pinned `specs/v0.1.0.md`; `taskrail validate` passed and `next --json`
  selected T-058 before lifecycle writes. Base: origin/main 805c34d.
- Added a discriminator type check before hash-based dispatch, loader tests for
  arrays/objects, valid duration controls, and CLI invalid-kind controls in both
  output modes. Updated the user-facing changelog.
- Strict TDD: `uv run pytest tests/unit/experiment_test.py -k duration_kind -q`
  initially returned 6 failures (unhashable list/dict or exit 1), 11 passes.
  After the minimal guard, the full experiment file passed all 56 tests.
- Dedicated Task simplifier loaded `code-simplifier`: no edits needed.
- Parallel independent Task reviewers loaded `code-reviewer` in General,
  Security, and Python lanes, with their indexed reviewers/companions. All
  returned: "No concrete task-relevant findings." Security was selected for
  untrusted input and overwrite integrity; Python for discriminator semantics.
  Database/framework/domain lanes were omitted because no corresponding
  contracts changed. Three lanes remained within the specialist budget.
- Fresh candidate-validation Task confirmed the empty candidate set. No finding
  IDs, rejections, fixes, deferrals, or follow-ups. Fresh disposition-verification
  Task confirmed: "No concrete task-relevant findings." One review cycle.
- Manual separate-process CLI checks for arrays/objects, with and without
  `--overwrite`: all returned JSON errors and exit 2, no stderr or staging output,
  and byte-identical retained artifacts. Temporary fixtures were removed.
- Final `mise run check`: Ruff lint/format passed, strict mypy passed (60 source
  files), pytest passed (805 tests), and all five shell guard suites passed.
- `mise run test:mutate`: scoped to `merge_carlo.experiment`, efficacy
  650/728 (89.3%), floor passed. Remaining module survivors are not hidden or
  waived; no full-repository mutation claim is made.
- `mise run setup` installed hooks; maintainer git identity retained.
- 2026-10-04T21:47:44Z: verification pass
