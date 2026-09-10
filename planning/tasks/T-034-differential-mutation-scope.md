---
id: T-034-differential-mutation-scope
title: Scope differential mutation verdicts to executed modules
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-004-fifo-review-engine
updated_at: "2026-09-10T13:00:24Z"
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

### Executed evidence (2026-09-10)

- Strict TDD: `bash scripts/check-mutation-floor-test.sh` first failed with
  `unknown argument: --module`; the runner fixture then failed on unrelated
  calendars at 0/10. Both now pass through the same shell suite.
- `mise run check` passed twice: Ruff, formatting, strict mypy (14 files),
  pytest (160 passed), and all policy/tooling shell suites.
- A disposable checkout with an engine-only comment diff and fresh mutation
  cache ran `BASE=HEAD bash scripts/mutate-diff.sh`: engine 254/262 (96.9%),
  pass. Raw `uv run mutmut results --all true` still included calendars
  0/61, not checked. Unscoped reporting of that output failed as expected.
- Subsequent `uv run mutmut run` and unscoped reporting passed: engine
  254/262, calendars 58/61, CLI 2/3 (insufficient evidence). No raw mutant
  was excluded from its module denominator.
- Dedicated code-simplifier review recommended no changes. General independent
  code-reviewer lane and fresh candidate validation both concluded:
  "No concrete task-relevant findings." No specialist language/framework,
  security, or database lane applies to this Bash/AWK-only change.
- No findings needed fixes or deferrals; no new v0.1.0 follow-up was exposed.
  T-033 discovery coverage and T-030 release validation remain separate work.

## Implementation Notes

Filed during T-004; no tooling fix implemented in that task. Relevant owners:
`scripts/mutate-diff.sh` and `scripts/check-mutation-floor.sh`.
- 2026-09-10T13:00:24Z: verification pass
