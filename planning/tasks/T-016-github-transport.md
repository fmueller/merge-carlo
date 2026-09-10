---
id: T-016-github-transport
title: Provide a read-only rate-limited GitHub transport
status: completed
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-015-offline-demo
updated_at: "2026-09-10T18:02:37Z"
---

# T-016-github-transport Provide a read-only rate-limited GitHub transport

## Description

Provide the read-only GitHub transport: an explicit configurable API version
recorded in every extraction manifest, required headers, pagination by link,
conditional requests where applicable, bounded retries with jitter, and respect
for rate limit and `Retry-After` headers. Authentication and permission failures
are distinguished from retryable ones. Redirects and pagination targets are
restricted to the approved API origin.

## Acceptance

- The adapter exposes no method that creates a review, merges, changes labels, assigns a reviewer, or administers a repository.
- A redirect or pagination link to another origin is refused, so credentials are never forwarded.
- A rate-limit response is retried per the documented headers; a permission failure is not retried.
- Tokens are read from the environment and are redacted in every diagnostic, error, and log line.
- Configurable request, page, payload, and record limits are enforced.

## Verification Notes

- Fixture-backed tests including pagination, rate-limit retry, and permission denial.
- A test asserting no token substring appears in any captured log or exception text.

## Implementation Notes

### Outcome and scope

Implemented the serial GET-only Python transport in `src/merge_carlo/github.py`.
GitHub.com is the only approved origin; API version is configurable and attached
to every result. Earlier pages survive later failures as partial collections.
Request/page/payload/record limits, conditional headers, rate-limit deadlines,
bounded jitter retries and fixed diagnostics are documented in
`docs/github-transport.md`. No CLI, cohort collection, extraction writer or
SQLite store was added; those remain later v0.1.0 tasks. Future extraction
writers must copy the result API version into their manifests.

### Workflow-v3 evidence

1. Understand: inspected the task, active ingestion spec and surrounding package
   contracts. Started from the requested origin/main after T-015; Taskrail
   validation passed and deterministic next selected T-016. Setup installed hooks.
2. TDD: first `uv run pytest tests/unit/github_test.py -q` failed collection with
   `ModuleNotFoundError: No module named 'merge_carlo.github'`. Initial transport
   tests then passed. Secondary-rate and reflected-debug-log tests independently
   failed before their fixes. All final 66 transport tests pass.
3. Initial checks: Ruff, strict mypy and 443 tests passed before review.
4. Dedicated code-simplifier Task loaded its skill and replaced generic validator
   list comprehensions/unpacking with explicit validator handling. Accepted that
   narrow simplification; focused tests, Ruff and mypy passed afterward.
5. Separate parallel General, Security and Python Tasks loaded code-reviewer and
   the mapped ECC reviewers. General loaded common rules; Security loaded
   security-review and common security; Python loaded python-patterns. These
   lanes cover the network/auth boundary and Python implementation. Database,
   frameworks, ML and network-configuration lanes were omitted: no persistence,
   framework, modeling or network infrastructure changes. A fresh candidate
   validator confirmed two findings and rejected one as outside the transient
   transport contract. Python: "No concrete task-relevant findings."
6. Dispositions: both validated findings fixed (details below), no deferrals.
7. Two review-fix-recheck cycles. First disposition verification found negative
   and fractional Retry-After values still bypassed the conservative fallback;
   second fix rejected malformed numeric syntax. A fresh final verifier marked
   both findings RESOLVED and returned "No concrete task-relevant findings."
   Final `mise run check`: 455 passed, Ruff and format clean, mypy clean across
   36 files, commit/push/author/mutation/orb policy guard suites all passed.
8. Finalization only after the above gates: Taskrail verification/completion and
   safe fetch/reconciliation, maintainer-identity commit and authorized main push.

### Verbatim review findings and disposition

- GEN-T016-002: "A malformed `Retry-After` on a rate-limit response causes an
  aggressive one-second retry, contradicting the documented conservative
  rate-limit policy." Fixed by separating valid deadlines from conservative
  rate-limit fallback and accepting only ASCII decimal delay-seconds. First
  review-fix red command `uv run pytest tests/unit/github_test.py -q -k
  'origin_is_not or retry_header_variants'`: 2 failed, 4 passed. Second-cycle red
  command `uv run pytest tests/unit/github_test.py -q -k retry_header_variants`:
  4 failed, 5 passed for -1, 1.5, +1 and 1e1. Final targeted suite: 66 passed.
- SEC-001: "The transport exposes out-of-scope arbitrary HTTPS origins and
  forwards `GITHUB_TOKEN` to them, expanding the credential trust boundary
  beyond the spec-approved GitHub origin." Fixed by removing custom-origin
  configuration and pinning GitHub.com, retaining exact origin checks on every
  target. Constructor-surface test failed before removal; final tests pass.
- Rejected candidate GEN-T016-001: "JSON escaping bypasses the
  credential-in-response guard, allowing a decoded `Collection.records` value
  to contain the environment token despite the transport’s credential-secrecy
  contract." Validator reproduced the byte-check bypass but rejected the
  claimed T-016 invariant: records are intentionally transient raw JSON, not
  persisted artifacts or diagnostics. Projection/privacy belongs to T-017.
  No validated finding was silently dropped or deferred.

### Mutation evidence and known reporting limitation

`BASE=57c2c2941bc2d734798d0fd54b8b87ffe1303d1c mise run test:mutate` ran only
`merge_carlo.github.*`. Initial raw result: 405 killed, 4 timeout, 116 survived,
525 total (77.90%). Meaningful coverage was strengthened for streaming bounds,
resource closure, validators, token syntax, prefix preservation and retry-budget
reset. Final raw result: **436 killed, 9 timeout, 84 survived, 529 total,
445/529 = 84.12% efficacy**, zero unexecuted. No exclusions, survivor suppression,
denominator adjustment or policy changes. Header-name casing mutants are examples
of equivalent survivors; all survivors remain in the raw denominator.

The wrapper still reports missing results because existing T-038 excludes
Unicode-mangled class-method identifiers. Retaining raw output, the unchanged
guard passes with only identifier separators normalized:
`sed 's/ǁ/__/g' <raw-results> | bash scripts/check-mutation-floor.sh --module
merge_carlo.github` -> `445/529 84.1% ok`. The 80% floor and scoped execution
requirements remain unchanged. T-038 already tracks this v0.1.0 release blocker;
no duplicate task or second implementation was added here.

### Manual evidence and follow-ups

Five offline manual API steps passed in a temporary directory: public GET-only
surface, paginated retry with exact wait/version, cross-origin redirect/link
refusal, permission denial with private diagnostics, and all four limits.
Plan/report: `planning/artifacts/manual-test/T-016-github-transport/20260910T175249Z/`.
Temporary helper removed. No live GitHub requests or sensitive data used.

No new follow-ups filed. Existing T-038 is applicable before v0.1.0 release;
T-017 owns projected-store privacy and T-018 owns cohort extraction. Neither was
implemented in this task. Exact recommended next task: T-017-projected-store.
- 2026-09-10T18:02:37Z: verification pass
