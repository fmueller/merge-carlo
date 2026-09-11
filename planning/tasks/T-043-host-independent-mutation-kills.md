---
id: T-043-host-independent-mutation-kills
title: Make timezone and SQLite URI mutation kills independent of the host
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-11T13:21:30Z"
---

# T-043-host-independent-mutation-kills Make timezone and SQLite URI mutation kills independent of the host

## Description

The T-030 release mutation gate passes both locally and in GitHub run
34601538915. Twelve mutants are killed locally but survive on CI, because the
tests that kill them depend on the host (see `docs/mutation-policy.md`, "CI
run"):

- Seven `astimezone(UTC)` -> `astimezone(None)` mutants: `attribution`
  `_timestamp` 13, `features` `build_features` 395, `simulation.calendars`
  `_local_to_utc` 9, and `validation` `replay_held_out` 26, 28, 100, and 101.
  They are killed only when the host zone is not UTC. Locally, calendars 9
  fails 10 tests under CEST and none under `TZ=UTC`, and attribution 13 fails
  3 under CEST and none under `TZ=UTC`.
- Five SQLite `uri=` mutants: `inspection` `_read_dataset` 17, 19, and 23, and
  `store` `ProjectedStore.__init__` 5 and 7. They are killed only when SQLite
  was built without `SQLITE_USE_URI`. The locked uv interpreter's SQLite 3.50.4
  lacks it; Ubuntu system SQLite 3.45.1 has it.

On a UTC host with URI-enabled SQLite, a regression to host-local time or to
path-interpreted database names would pass the suite. The spec requires
timezone-aware UTC bounds and a read-only projected store ("Release
Hardening"), and neither should depend on where tests run.

## Acceptance

- The timezone behavior is asserted independently of the host zone. For
  example, a test runs under a pinned non-UTC zone, or asserts that results
  carry UTC `tzinfo` rather than only equal instants. The seven mutants are
  then killed under both `TZ=UTC` and a non-UTC zone.
- Read-only and existing-only database opening is asserted independently of
  SQLite's `SQLITE_USE_URI` build option, so the five mutants are killed on
  both builds, or any mutant that is genuinely equivalent on one build is
  recorded with its reason.
- No production behavior changes solely to suit the tool, and no test is
  shaped to the mutants rather than to specified behavior.
- A GitHub `Mutation tests` run reports these mutants as killed, and the
  affected modules' CI counts match the local counts.

## Verification Notes

- Locally, apply each mutant with `uv run mutmut apply` and run the covering
  tests under the default zone and under `TZ=UTC`.
- Dispatch the mutation workflow and diff `mutation-results.txt` against a
  local full run.

## Implementation Notes

Filed from T-030's CI verification. Not started.
