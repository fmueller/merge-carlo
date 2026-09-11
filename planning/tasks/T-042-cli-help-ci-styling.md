---
id: T-042-cli-help-ci-styling
title: Keep the CLI help test independent of CI terminal styling
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-11T12:55:51Z"
---

# T-042-cli-help-ci-styling Keep the CLI help test independent of CI terminal styling

## Description

The Build workflow has been red since `85169cf` (T-028), and the T-030 mutation
workflow dispatch (run 34601152100) failed while collecting stats. Both failed
on one test: `tests/unit/cli_test.py::test_help_describes_the_tool`. Typer
forces a styled Rich console when `GITHUB_ACTIONS`, `FORCE_COLOR`, or
`PY_COLORS` is set (`typer/rich_utils.py` `FORCE_TERMINAL`), so on CI the
`--help` output renders `--json` as two ANSI-styled segments and the substring
assertion fails. Locally the output is unstyled and the test passes.

The CLI contract (specs/v0.1.0.md "Release Hardening": `--help` and a
machine-readable console mode) is unchanged. Only the test's reading of the
help text depends on the terminal environment.

## Acceptance

- `test_help_describes_the_tool` passes with `GITHUB_ACTIONS=true`,
  `FORCE_COLOR=1`, and a plain environment, and still asserts that the help
  text describes the tool and lists `--json`.
- The CLI's production help rendering is not changed.
- The Build workflow on `main` is green on Python 3.12, 3.13, and 3.14.

## Verification Notes

- Before the fix, `GITHUB_ACTIONS=true uv run pytest tests/unit/cli_test.py`
  reproduced the CI failure locally: 1 failed, 18 passed.
- After the fix, run the CLI tests under each environment above, run the full
  suite with `GITHUB_ACTIONS=true`, and record the Build run on the pushed commit.

## Implementation Notes

The test strips ANSI SGR sequences from the help output before asserting. A
`CliRunner` environment override would not help, because Typer reads the
variables at import time. `typer` does not re-export `unstyle`, and `click` is
only a transitive dependency, so a local regex avoids a new import.
