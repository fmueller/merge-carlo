---
id: T-058-reject-nonscalar-model-duration-discriminators
title: Reject nonscalar model duration discriminators without crashing
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-10-04T20:40:56Z"
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
