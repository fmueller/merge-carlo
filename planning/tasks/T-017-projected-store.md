---
id: T-017-projected-store
title: Persist projected observations in a migrated SQLite store
status: completed
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-016-github-transport
updated_at: "2026-09-10T18:28:10Z"
---

# T-017-projected-store Persist projected observations in a migrated SQLite store

## Description

Persist projected observations in SQLite with explicit migrations and
foreign-key checks: extractions, pull requests, reviews, lifecycle events,
optional CI observations, derived features, collection status, and schema
migrations. Drop bodies, descriptions, diffs, patches, commit messages, email
addresses, avatars, and check output before storage. Content hashes cover sorted
normalized records and canonical JSON.

## Acceptance

- Migrations apply from empty and are recorded; foreign keys are enforced.
- No full raw API payload is persisted by default.
- The same semantic content hashes identically regardless of page layout or extraction completion order.
- Actor identifiers in analytical exports are workspace-scoped HMAC pseudonyms whose mapping and secret stay outside shareable artifacts, with restrictive local permissions.
- All SQL is parameterized.

## Verification Notes

- Privacy tests asserting bodies, patches, emails, and tokens never appear in stored projections.
- A hash-stability test over two differently ordered extractions of the same content.

## Implementation Notes

- Added the offline `merge_carlo.store` Python API: typed allowlist projections,
  schema-1 migration ledger and foreign-key checks, atomic extraction replacement,
  explicit collection statuses, pre-storage workspace HMAC actor identities and
  versioned canonical exports. See `docs/projected-store.md` for the contract.
- Workflow-v3 steps 1–3: acceptance/spec inspection; initial test collection failed
  with missing `merge_carlo.store`, then six tests passed. Added interruption and
  static-open-error regressions: two failed, then all 20 focused tests passed.
  The initial full suite passed 475 tests; strict mypy and Ruff passed.
- Step 4: dedicated code-simplifier subagent loaded its skill; simplified exception
  branches and reused the extraction ID string. No behavioral/schema changes;
  focused tests, Ruff, format and mypy passed after integration.
- Steps 5–6: four independent code-reviewer subagents ran General, Python,
  Database and Security lanes with routed ECC/companion guidance. Each concluded
  verbatim: "No concrete task-relevant findings." A fresh candidate-validation
  subagent confirmed zero candidates, rejections or duplicates. No deferrals.
  Three specialists cover language, persistence and trust boundaries; no web
  framework or other domain lane applies. No additional Amp threads were created.
- Step 7: strengthened export shape, key safety, cascade cleanup and migration
  failure tests after raw mutation inspection. Final `mise run check` passed:
  Ruff, format, strict mypy (38 files), 486 pytest tests and all shell guard suites.
  `uv run pytest tests/unit/store_test.py -q`: 31 passed. A fresh disposition
  reviewer approved with "No concrete task-relevant findings." One review cycle.
- Scoped `BASE=origin/main mise run test:mutate` passed. Initial raw store result:
  273 killed / 380 total (71.8%); final: 321 killed / 380 (84.5%), 59 survived,
  zero unchecked/timeouts. Existing guard reports only 11/12 (91.7%) because the
  already-tracked T-038 parser omits class-method names. Both counts are reported;
  no exclusions or policy changes. The surviving canonical mutant changing
  `allow_nan=False` to `None` is equivalent and remains counted. Mutation evidence
  includes export collection-status-key regression changing survived to killed.
- Manual test: five acceptance-derived checks passed in disposable databases,
  including cross-file hash stability, byte-level privacy, rollback/reopen and
  private key continuity/permissions. Ephemeral plan/report:
  `planning/artifacts/manual-test/T-017-projected-store/20260910T182429Z/`.
- Existing T-038 covers the mutation-reporting limitation for v0.1.0; no duplicate
  follow-up filed. Cohort/resume collection remains T-018; readiness/origin
  resolution remains T-019. Neither was implemented here.
- 2026-09-10T18:27:59Z: verification pass
