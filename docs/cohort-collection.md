# Cohort collection

Use only a repository you are authorized to analyze. Credentials come from
`GITHUB_TOKEN`, never a command-line argument. Collection performs GETs only.

```bash
uv run merge-carlo collect --repo OWNER/REPO \
  --start 2026-01-01T00:00:00Z --end 2026-02-01T00:00:00Z \
  --out out/cohort --workspace /private/path/merge-carlo-key
```

The workspace directory is created owner-only if absent, must have an existing
parent, and must be outside the dataset. Keep it private and reuse it across
extractions for stable actor pseudonyms. The dataset directory must be empty or
absent. Its `dataset.sqlite` contains projected observations, not raw responses.
Do not run multiple collectors against the same dataset concurrently.

Repeat the command with `--resume` to reconcile an existing extraction. The
repository's immutable ID, analysis interval and API version must match. Each
run enumerates all states and currently open PRs from page one, follows Link
pagination, and unions immutable IDs. There is no update-time cutoff. The cohort
includes creations in `[start, end)` and older PRs whose current open/closing
evidence overlaps the interval; uncertain close times are retained conservatively.
Reopened PRs remain in totals; fit exclusions and readiness inference are T-019.

Reviews and issue lifecycle events are paginated for every selected PR. This is
the issue-events endpoint, not the non-archival repository activity Events API.
Non-lifecycle events such as labels are discarded. CI and derived features are
explicitly `not_requested`. Malformed projected records or ambiguous duplicate
snapshots yield `partial`; newer PR `updated_at` values supersede older ones.
Collection is not a point-in-time transaction on GitHub: concurrent changes or
deletions can still prevent reconstructing an exact historical repository state.

`--api-version`, `--max-pages`, `--max-requests`, `--max-records` and
`--max-payload-bytes` configure the bounded transport. Budgets apply per
collection (payload bytes per page), not to the whole extraction. A limit or
failed child collection cannot become empty complete history. Exit codes are
0 for complete requested collections, 3 for incomplete/source data or access
failure, and 2 for invalid input. Inspect statuses in the SQLite export to
distinguish partial, unavailable and not requested.

A first extraction writes an incomplete manifest before enumerating PRs. Final
replacement is transactional; an interruption preserves that partial marker or
the prior extraction. Resume replaces observations and children rather than
appending duplicates or reusing a saved page offset.

Analysis bounds, retrieval completion time, and source/observation timestamps
are distinct. PR and mutable review records carry `observed_at` (collection
completion time, conservatively later than every page). Lifecycle events retain
`created_at`. `ProjectedStore.historical(id, cutoff)` excludes snapshots observed
after the cutoff and undated legacy snapshots; it filters lifecycle events by
source time. This conservative reader is not a calibrated feature pipeline, and
does not certify history completeness. Read statuses from `export` alongside it.
Snapshot observation time affects semantic hashes; identical observations at the
same observation time hash independently of page order. Resume at a later time
can legitimately change the content hash even if the API fields do not change.

All verification uses synthetic HTTP fixtures. Live GitHub collection has not
been tested; calibration, origin attribution and the inspection CLI are pending.
