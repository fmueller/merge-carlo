---
id: T-047-ci-python-matrix
title: Run the CI test matrix on each listed Python version
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-15T11:10:40Z"
---

# T-047-ci-python-matrix Run the CI test matrix on each listed Python version

## Description

The Build workflow lists Python 3.12, 3.13, and 3.14, but every unit-test job
ran on 3.13. uv prefers the `.python-version` file (3.13) over the interpreter
`actions/setup-python` puts on PATH, so `uv sync` created each job's `.venv` on
3.13. Run 34799109648 shows `Using CPython 3.13.15` and pytest on 3.13.15 in
the 3.12 and 3.14 jobs. The supported floor (3.12) and the newest version
(3.14) were therefore never tested in CI.

The release gate in specs/v0.1.0.md "Release Hardening" requires tests to pass;
this makes the matrix test what it names.

## Acceptance

- Each unit-test job sets `UV_PYTHON` to its matrix version.
- The full suite passes locally on Python 3.12 and 3.14.
- On the next Build run, each unit-test job logs pytest on its own matrix
  version.

## Verification Notes

- Before the fix, run 34799109648 logged `Using CPython 3.13.15` and pytest
  on 3.13.15 in the "Python 3.12" and "Python 3.14" jobs.
- Verify run on 2026-09-15 passed locally: ruff, format, mypy, the guard
  suites, and 685 tests each on Python 3.12.3 and 3.14.2.
- The release, test-index, and mutation workflows run a single interpreter
  from `.python-version` by design and need no change.
- Build run 34961700906 on the fix passed. The unit-test jobs logged pytest
  on CPython 3.12.14, 3.13.15, and 3.14.7 respectively, 685 passed each.

## Implementation Notes

- 2026-09-15T11:08:35Z: verification pass
