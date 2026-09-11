---
id: T-041-cli-command-mutations
title: Cover decorated CLI commands in mutation testing
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-015-offline-demo
updated_at: "2026-09-11T10:58:54Z"
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

Resolution (2026-09-11, maintainer decision): documented scoped alternative for
v0.1.0. mutmut 3.7.0 skips decorated functions
(`mutmut/mutation/file_mutation.py:286-291`), upstream main still does, and
boxed/mutmut#387 is open, so Typer command bodies cannot be discovered without
restructuring the CLI. The limitation is recorded in `docs/mutation-policy.md`
("Discovery limitations in v0.1.0"), `docs/limitations.md`, and
`docs/implementation-status.md`, and locked by
`tests/unit/documentation_test.py::test_mutation_discovery_limitations_are_explicit`.

Scoped run: `uv run mutmut run "merge_carlo.reporting.*" "merge_carlo.cli.*"`
(12.8 s wall). `merge_carlo.cli` 74/90 (82.2%), guard verdict `ok`; mutated
functions `_emit`, `_print_version`, `JsonTyperGroup.main`. The instrumented
`mutants/src/merge_carlo/cli.py` has trampolines only for those three, none for
the `main` callback or the `schema`, `demo`, `collect`, `inspect`, and `validate`
commands. Since T-015, the module has gained enough discovered helper mutants for
a verdict; that verdict still does not cover the command bodies.

Behavioral tests are retained unchanged: option forwarding and synthetic
labeling (`tests/integration/demo_test.py::test_offline_demo_reproduces_complete_synthetic_output`),
no credentials, HTTP client, or socket (same test), invalid options exit 2
without writing (`test_invalid_demo_options_do_not_write`), existing-output
preservation (`test_demo_preserves_existing_output`), and exit codes 2, 3, and 4
across `schema`, `collect`, and `validate` in `tests/unit/cli_test.py`.
- 2026-09-11T10:58:54Z: verification pass
