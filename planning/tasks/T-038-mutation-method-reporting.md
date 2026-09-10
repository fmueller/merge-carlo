---
id: T-038-mutation-method-reporting
title: Count mangled class methods in mutation efficacy reports
status: todo
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-10T15:48:51Z"
---

# T-038-mutation-method-reporting Count mangled class methods in mutation efficacy reports

## Description

Release assignment: v0.1.0, before the release mutation gate. The current
`scripts/check-mutation-floor.sh` identifier regex excludes mutmut class-method
names containing the Unicode separator `ǁ`. T-012 discovered 170 runner mutants
(161 killed, nine survived), but the guard counted only eight top-level mutants
(five killed), incorrectly labeling the module insufficient evidence. Preserve
raw reporting and the 80% per-module floor while recognizing all emitted names.
This differs from T-033: these methods are discovered and executed, then dropped
by the report parser. Do not restructure production code to accommodate tooling.

## Acceptance

- Full and scoped reports count mangled class-method and top-level mutants in
  their owning module, including killed, survived, timeout and not-checked rows.
- Unexecuted selected class-method mutants fail the scoped gate, and unrelated
  modules do not influence the selected module's verdict.
- Existing raw counts, minimum sample policy and v0.1.0 80% floor are unchanged.

## Verification Notes

- Add shell regression fixtures with actual `xǁExperimentRunǁ_iterate__mutmut_1`
  names and mixed top-level names; test full/scoped and unexecuted behavior.
- Compare the report with raw `uv run mutmut results --all true` output.

## Implementation Notes

Filed during T-012, not implemented in that task. Initial reproduction:
`BASE=11072f440ea1350327ab23e65ef16a05cd97619d mise run test:mutate`.
