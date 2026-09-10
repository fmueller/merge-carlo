---
id: T-034-differential-mutation-scope
title: Scope differential mutation verdicts to executed modules
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-004-fifo-review-engine
updated_at: "2026-09-10T11:57:25Z"
---

# T-034-differential-mutation-scope Scope differential mutation verdicts to executed modules

## Description

Release assignment: v0.1.0, required before the release mutation gate.
The differential runner selects only changed modules but passes all discovered
mutants to the efficacy guard. On a fresh T-004 run, engine scored 245/262
(93.5%) while untouched calendars appeared as 0/61 (not executed), causing a
false failure. Scope differential verdicts to the selected execution set while
preserving the full gate's per-module accountability. This is distinct from
T-033's omitted dataclass-method discovery issue.

## Acceptance

- A clean-cache differential run judges only modules selected by its diff.
- Unexecuted or stale results from unrelated modules cannot fail or inflate
  the differential verdict; missing execution in selected modules cannot pass.
- The full mutation gate still checks every discovered module independently.
- Shell regression fixtures cover selected, unrelated, and missing results.

## Verification Notes

- Reproduce with an engine-only diff and a fresh mutmut cache; compare the
  selected run output with `mutmut results --all true`.
- Run script tests and both differential and full reporting checks.

## Implementation Notes

Filed during T-004; no tooling fix implemented in that task. Relevant owners:
`scripts/mutate-diff.sh` and `scripts/check-mutation-floor.sh`.
