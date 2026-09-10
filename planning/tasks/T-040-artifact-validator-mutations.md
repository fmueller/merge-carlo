---
id: T-040-artifact-validator-mutations
title: Cover Pydantic artifact validators in mutation testing
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-014-experiment-artifacts
updated_at: "2026-09-10T16:59:55Z"
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
