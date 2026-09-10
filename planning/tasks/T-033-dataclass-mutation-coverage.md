---
id: T-033-dataclass-mutation-coverage
title: Cover dataclass simulation methods in mutation testing
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-003-duty-calendars
updated_at: "2026-09-10T11:40:11Z"
---

# T-033-dataclass-mutation-coverage Cover dataclass simulation methods in mutation testing

## Description

Release assignment: v0.1.0 (applies before the release mutation gate).

T-003's differential mutation run discovers 61 calendar mutants, all in the
top-level helpers and run-bound function. It discovers none in the decorated
dataclasses, including DutyCalendar.materialize and its absence/union logic.
The 58/61 score therefore does not establish mutation efficacy for those
methods. Restore meaningful method coverage without restructuring the model
solely for the mutation tool. Coordinate with T-030's broader efficacy gate.

## Acceptance

- Differential mutation testing discovers and executes mutations inside
  decorated simulation dataclass methods, including calendar materialization
  and lifecycle transitions.
- The per-module report cannot imply coverage of methods omitted by discovery;
  any unavoidable excluded method has an explicit limitation.
- Existing behavioral tests distinguish meaningful wrong implementations;
  equivalent mutants remain documented rather than suppressed.
- Full and differential mutation commands retain their existing scope and the
  documented runtime expectations.

## Verification Notes

- Compare `uv run mutmut results --all true` discovery before and after changes.
- Exercise `BASE=<base-ref> mise run test:mutate` and the T-030 full gate;
  record which methods were mutated, per-module efficacy, and runtime.

## Implementation Notes

Originating evidence: T-003 calendar tests and review identified the gap;
`src/merge_carlo/simulation/calendars.py` and `pyproject.toml` define the relevant
implementation and mutation configuration. This task was filed, not implemented,
as part of T-003. No dependency or architecture remedy has been chosen.
