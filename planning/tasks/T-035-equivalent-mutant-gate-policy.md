---
id: T-035-equivalent-mutant-gate-policy
title: Define auditable equivalent-mutant gate policy
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-10T12:45:37Z"
---

# T-035-equivalent-mutant-gate-policy Define auditable equivalent-mutant gate policy

## Description

Release assignment: v0.1.0, needed to resolve the T-005 verification blocker
before release. The maintainer explicitly selected an 80% raw per-module gate
for v0.1.0 on 2026-09-10, superseding the initial manual-equivalence proposal.
Implement that threshold narrowly, preserving raw counts and outcomes rather
than excluding mutants. This is distinct from T-034 (unexecuted module
accounting). No T-005 implementation belongs in this task.

T-005 reported 34/39 (87.2%) against the 90% floor. Its proposed equivalents
were error-message wrapping (7), omission of default ensure_ascii=True (14),
changing an unused dictionary separator for an array (24), ASCII encoding
name case (29), and omission of default big-endian byte order (34).
All five remain in the denominator. Preserve the historical failed run;
the new threshold does not imply that test efficacy improved.

## Acceptance

- Default the shared mutation guard to 80%, explicitly scoped to v0.1.0.
- Preserve raw results, per-module accountability, the ten-mutant minimum,
  explicit threshold overrides, and failures below the selected floor.
- Cover the 80% boundary, a weak module masked by a stronger module, and raw
  34/39 passing at 80% but failing at 90%, without survivor exclusions.
- Document the authorized relaxation and later-release reassessment; no
  manual-equivalence override or T-005 stream behavior change is introduced.

## Verification Notes

- Run `bash scripts/check-mutation-floor-test.sh` red then green.
- Run applicable guard regression suites and `mise run check`.
- T-005's owner must reproduce mutation results on its isolated implementation;
  no T-005 code or mutation results are imported into this checkout.

## Implementation Notes

Recovered the task intent from its unpushed planning record and registered it
with `taskrail task new` on the requested baseline. The remote backlog still
recommends T-005; this task is the explicit user-selected prerequisite.

### Superseded draft history (not the shipped policy)

An earlier documentation-only manual-equivalence proposal was reviewed but
never committed or pushed, and its disposition document was removed. The exact
G-001 finding was: "Clarify that the SHA-256 manifest excludes its own file;
otherwise the evidence requirement is self-referential and cannot be
reproduced exactly." It was resolved in that draft by excluding the manifest
from its enumerated evidence files; review then reported "No concrete
task-relevant findings." Because the entire proposal was superseded, neither
the finding nor its disposition applies to the shipped 80% policy.

The superseded verification passed `mise run check` with 160 tests and all
lint, type, and guard checks, while the unchanged guard rejected synthetic
34/39 results at 90%. Those results verify only the abandoned draft. Final
verification for the replacement policy is recorded separately below. T-005's
raw 34/39 history remains unchanged, and T-005, T-030, T-033, and T-034 remain
separate work.
- 2026-09-10T12:33:35Z: verification pass

### Final 80% policy workflow

1. Understand: the explicit maintainer decision supersedes the manual-score
   proposal. The shared guard is the source of truth for differential, full,
   and CI mutation gates. Raw statuses/counts and ten-mutant minimum stay intact.
2. Strict TDD: `bash scripts/check-mutation-floor-test.sh` failed with
   `FAIL: at-floor was rejected` and `8/10 80.0% BELOW FLOOR 90%` (exit 1).
   Changing only the default to 80 yielded `mutation floor checks passed`.
   Fixtures also cover 7/10 rejection, 10/10 plus 7/10 per-module rejection,
   and raw 34/39 = 87.2% passing at 80 but failing at explicit 90.
3. Initial `mise run check` passed Ruff, format, strict mypy (14 files), 160
   tests, and all five shell guard suites; Taskrail validation and diff check
   also passed.
4. Dedicated `code-simplifier` removed redundant code comments and condensed
   the superseded history, retaining the exact prior finding. Accepted: the
   final production diff is solely `floor=90` to `floor=80`, with v0.1.0 scope
   in contributor guidance, policy, changelog, and regression fixtures.
   Simplifier reran the shell suite, full check, diff check, and validation:
   all passed.
5. Independent General lane loaded `code-reviewer`, reviewer-index, and ECC
   General guidance: "No concrete task-relevant findings." No specialist
   lanes apply to a shell constant/docs change; no Python, framework, database,
   or security-boundary behavior changed. A fresh candidate-validation reviewer
   loaded the skill and confirmed an empty candidate set, no rejected findings.
6. No final-policy findings required fixes or deferral. Historical G-001 is
   resolved by removal of the superseded mechanism; no operative remnant exists.
7. Final `mise run check`: 160 passed, Ruff/format, strict mypy (14 files), all
   five shell suites passed. Diff check and Taskrail validation passed.
   Differential mutation skipped because no source modules changed (no score
   claimed). Fresh `code-reviewer` disposition verification: G001 RESOLVED,
   "No concrete task-relevant findings." One final-policy review/recheck cycle.
8. Fresh Taskrail verification follows these gates. Completion was retained
   by the CLI; only this task's implementation is shipped. T-036 is filed only.

Taskrail rejected reopening the earlier completed state through `start`,
`block`, and `unblock`. T-036 records the missing CLI capability, explicitly
applicable to v0.1.0 workflow tooling but not a release correctness blocker.
No machine-managed field was hand-edited. Fresh final verification is required
before committing this revised policy, regardless of the retained status.
- 2026-09-10T12:45:37Z: verification pass
