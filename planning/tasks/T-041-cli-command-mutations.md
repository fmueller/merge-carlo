---
id: T-041-cli-command-mutations
title: Cover decorated CLI commands in mutation testing
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-015-offline-demo
updated_at: "2026-09-10T17:23:17Z"
---

# T-041-cli-command-mutations Cover decorated CLI commands in mutation testing

## Description

Release assignment: v0.1.0, before the release mutation gate. T-015 adds a
Typer-decorated demo command, but the scoped mutmut run still discovers only
three mutants in `_print_version` and none in `demo` or the callback. Behavioral
CLI tests cover offline execution, invalid inputs and preservation of existing
output; the mutation score does not establish efficacy for those command paths.
Coordinate with T-033 and T-040 discovery work, without restructuring production
CLI code solely for the mutation tool. This is not T-038's result-parser issue.

## Acceptance

- Discover and execute meaningful mutations in decorated CLI command bodies,
  or document an explicit scoped alternative if the pinned tool cannot do so.
- Preserve raw reporting, the v0.1.0 80% floor, the minimum sample policy, and
  differential scope. Do not present undiscovered code as mutation-covered.
- Keep behavioral tests for option forwarding, error exit semantics, no network
  or credentials, synthetic output labeling, and existing-data preservation.

## Verification Notes

- Compare raw `uv run mutmut results --all true` and instrumented
  `mutants/src/merge_carlo/cli.py` before and after the change.
- T-015's scoped run reports only `_print_version` mutants: two killed and one
  equivalent survivor (`typer.Exit(code=None)` still exits zero). No `demo`
  mutants are discovered; the module correctly receives insufficient evidence.

## Implementation Notes

Filed, not implemented, during T-015. Scope is release-hardening verification,
not another demo feature or a change to the mutation floor.
