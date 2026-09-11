---
id: T-040-artifact-validator-mutations
title: Cover Pydantic artifact validators in mutation testing
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-014-experiment-artifacts
updated_at: "2026-09-11T10:58:54Z"
---

# T-040-artifact-validator-mutations Cover Pydantic artifact validators in mutation testing

## Description

Release assignment: v0.1.0, before the release mutation gate. T-014's scoped
mutmut run discovers top-level reporting helpers but no mutants for the
decorated Pydantic `Probability.check_probability` or `Summary.check_summaries`
validators. Behavioral malformed-artifact tests cover these methods, but the
reported mutation efficacy does not. This is discovery omission, not T-038's
Unicode method-name reporting bug. Coordinate with T-033's dataclass coverage
work without restructuring production contracts just to suit the mutation tool.

## Acceptance

- Discover and execute meaningful mutations in the artifact contract validators,
  or document an explicit scoped alternative if the pinned tool cannot do so.
- Preserve raw per-module reporting, the 80% v0.1.0 floor, and differential
  scope. Do not exclude survivors or count undiscovered code as covered.
- Tests distinguish invalid probability counts/bounds, denominator mismatches,
  nonfinite/unordered quantiles, and inconsistent summary totals/null reasons.

## Verification Notes

- Compare `uv run mutmut results --all true` before/after discovery changes.
- T-014 reporting has 235 top-level mutants and no result name containing
  `check_probability` or `check_summaries`; both methods remain uninstrumented
  in `mutants/src/merge_carlo/reporting.py`. Run a scoped differential check and
  record the raw count, discovered methods, and efficacy verdict.

## Implementation Notes

Filed, not implemented, during T-014. Existing functional regression tests must
remain; no mutation-tool workaround has been selected.

Resolution (2026-09-11, maintainer decision): documented scoped alternative for
v0.1.0. mutmut 3.7.0 skips decorated functions
(`mutmut/mutation/file_mutation.py:286-291`), upstream main still does, and
boxed/mutmut#387 is open, so the validators cannot be discovered without
restructuring production contracts. The limitation is recorded in
`docs/mutation-policy.md` ("Discovery limitations in v0.1.0"),
`docs/limitations.md`, and `docs/implementation-status.md`, and locked by
`tests/unit/documentation_test.py::test_mutation_discovery_limitations_are_explicit`.

Scoped run: `uv run mutmut run "merge_carlo.reporting.*" "merge_carlo.cli.*"`
(12.8 s wall). `merge_carlo.reporting` 231/243 (95.1%), guard verdict `ok`;
mutated functions `markdown`, `_number`, `_probability`, `_range`,
`render_report`, `wilson`. `mutants/src/merge_carlo/reporting.py` has no
trampoline for `check_probability` or `check_summaries`. The floor, raw
per-module reporting, and differential scope are unchanged.

Behavioral gaps closed in `tests/unit/reporting_test.py`:
`test_reject_defined_zero_trial_probability` (4 cases) and
`test_reject_inconsistent_summary_null_reasons` (3 cases). Deliberate
regressions of `reporting.py` fail them: removing the zero-trial rejection
fails 4; removing the undefined-summary rejection fails 2; dropping the
defined-quantile reason check fails 1. Restored, all 7 pass. Existing tests
already cover counts/bounds, denominator mismatches, nonfinite/unordered
quantiles, and inconsistent totals.
- 2026-09-11T10:58:54Z: verification pass
