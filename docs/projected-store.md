# Projected observation store

`merge_carlo.store` is an offline Python API. It does not collect a cohort or
provide `collect --resume`; those are downstream v0.1.0 work.

Create `WorkspaceKey.create(Path("private-workspace"))` once, outside any
shareable artifact directory. Reopen with `WorkspaceKey(Path("private-workspace"))`.
The directory is owner-only (0700), and `actor.key` is a random 32-byte secret
(0600). Existing unsafe permissions, symlinks, and invalid keys are rejected.
Back up this directory privately: there is no key recovery or automatic rotation.
No reversible actor mapping is retained. HMAC-SHA256 maps immutable GitHub actor
IDs into workspace-specific identifiers **before SQLite storage**, retaining actor
kind separately. Losing the key loses continuity; a store rejects a different key.
Pseudonymization is not anonymization. Repository IDs and activity remain sensitive.

```python
from pathlib import Path
from uuid import uuid4

from merge_carlo.store import Batch, Manifest, ProjectedStore, WorkspaceKey

key = WorkspaceKey.create(Path("private-workspace"))  # once only
extraction = Manifest.model_validate({
    "id": uuid4(),
    "repository_id": 17,
    "api_version": "2022-11-28",
    "analysis_start": "2026-01-01T00:00:00Z",
    "analysis_end": "2026-02-01T00:00:00Z",
    "retrieved_at": "2026-02-02T00:00:00Z",
})
with ProjectedStore(Path("observations.sqlite"), key) as store:
    store.save(extraction, [Batch("pull_requests", [], status="partial", reason="interrupted")])
    analytical_content = store.export(extraction.id)
    content_hash = store.content_hash(extraction.id)
```

## Projection and schema contract

Schema 1 holds `schema_migrations`, `workspace` (key fingerprint only),
`extractions`, `pull_requests`, `reviews`, `lifecycle_events`, `ci_observations`,
`derived_features`, and `collection_status`. Initialization and schema recording
are one write transaction. Reopening schema 1 is idempotent; unknown versions
are rejected, never downgraded. Each connection enables foreign keys and checks
existing references. Child observations refer to the PR within their extraction.
SQL binds all values; interpolated table names come only from source constants.

Only typed allowlisted fields survive projection: numeric immutable IDs, PR
numbers, constrained states, UTC timestamps, actor pseudonyms/kinds, commit SHA
identifiers, PR change counts, CI status/conclusion and readiness/origin fields
with provenance basis. Missing optional fields remain null. Raw titles, bodies,
descriptions, diffs, patches, commit messages, emails, logins, avatars, URLs and
check output are not stored. Invalid retained fields reject the entire save with
a static `StoreError`; they do not become missing observations. Config metadata
rejects extra fields and hides input values in validation-error text.

Lifecycle projections accept ready/draft, closed/reopened, merged, and
review-dismissed events. The collector selects supported event records; an
unsupported event cannot silently produce a complete empty history. CI inputs
are check-run shaped. Collection persists one derived attribution feature per
PR with readiness time, basis and policy; declared origin and resolution basis;
and mechanistic-fit eligibility with an explicit exclusion reason. Unknown
origin is never inferred from actor kind.

## Atomicity and semantic hashes

Pass **one reconciled batch per collection**, not one batch per HTTP page. Child
batches require `pr_id`, the immutable PR ID (not its repository-local number).
Identical duplicate records collapse. Conflicting duplicates and repeated batches
are rejected rather than resolved by arrival order. Batch order does not matter.
Every supplied batch preserves `complete`, `partial`, `unavailable`, or
`not_requested` and its constrained reason. Omitted batches are not declared
complete; unavailable/not-requested collections cannot contain observations.

`save` replaces only the named extraction in one transaction, including its old
children and statuses. A failure or interruption rolls back to the previous
extraction. Use separate connections in separate threads; SQLite serializes
writers with its bounded default busy timeout. Export reads one transactional
snapshot. Caller-owned raw inputs must not be mutated during a save.

Exports have `schema_version: 1`, projected table arrays, collection statuses and
semantic manifest fields. Hashes are SHA-256 over UTF-8 canonical JSON: sorted
keys, compact separators, finite values, normalized UTC timestamps, and sorted
deduplicated records. Extraction UUID and retrieval time remain in the local
manifest but are excluded from analytical content and its hash. Analysis bounds,
API version, repository, source timestamps and collection status are included.
Thus page layout and completion order do not change a hash, while an actual
observation or completeness change does. Hashes are workspace-specific because
actor pseudonyms are workspace-specific. Hashes never cover physical SQLite bytes.

Only export the analytical content, not the private workspace directory. The
local database is trusted application state, not an arbitrary imported SQLite
file. The caller owns file placement, access to observation files and exports,
batch sizing, cohort reconciliation and retention policy.
