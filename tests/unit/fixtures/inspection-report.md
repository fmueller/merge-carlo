# Dataset inspection

## Dataset coverage

- Analysis interval: `2026-01-01T00:00:00Z` (inclusive) to `2026-02-01T00:00:00Z` (exclusive)
- Retrieved at: `2026-03-01T00:00:00Z`
- API version: `2022-11-28`

## Counts

| Collection family | Records |
|---|---:|
| `pull_requests` | 3 |
| `reviews` | 1 |
| `lifecycle_events` | 2 |
| `ci_observations` | 0 |
| `derived_features` | 3 |

## Endpoint coverage

| Collection family | Complete | Partial | Unavailable | Not requested | Incomplete reasons |
|---|---:|---:|---:|---:|---|
| `pull_requests` | 0 | 1 | 0 | 0 | page_limit: 1 |
| `reviews` | 1 | 1 | 1 | 0 | permission: 1, unavailable: 1 |
| `lifecycle_events` | 1 | 1 | 1 | 0 | page_limit: 1, unavailable: 1 |
| `ci_observations` | 0 | 0 | 0 | 3 | none |
| `derived_features` | 3 | 0 | 0 | 0 | none |

## Date coverage

| Collection family | Timestamp | Observed | Earliest | Latest |
|---|---|---:|---|---|
| `pull_requests` | `created_at` | 3 | 2026-01-02T00:00:00Z | 2026-01-05T00:00:00Z |
| `pull_requests` | `updated_at` | 3 | 2026-01-03T00:00:00Z | 2026-01-16T00:00:00Z |
| `pull_requests` | `closed_at` | 2 | 2026-01-06T00:00:00Z | 2026-01-15T00:00:00Z |
| `pull_requests` | `merged_at` | 1 | 2026-01-15T00:00:00Z | 2026-01-15T00:00:00Z |
| `pull_requests` | `observed_at` | 3 | 2026-03-01T00:00:00Z | 2026-03-01T00:00:00Z |
| `reviews` | `submitted_at` | 0 | n/a | n/a |
| `reviews` | `observed_at` | 1 | 2026-03-01T00:00:00Z | 2026-03-01T00:00:00Z |
| `lifecycle_events` | `created_at` | 2 | 2026-01-03T00:00:00Z | 2026-01-04T00:00:00Z |
| `ci_observations` | `started_at` | 0 | n/a | n/a |
| `ci_observations` | `completed_at` | 0 | n/a | n/a |
| `derived_features` | `ready_at` | 2 | 2026-01-05T00:00:00Z | 2026-01-05T00:00:00Z |

## Attribution and readiness

- **Work origin:** ai 1 (33.3%), human 1 (33.3%), unknown 1 (33.3%)
- **Work origin unknown fraction:** 33.3%
- **Readiness basis:** created_at_proxy 1 (33.3%), observed_event 1 (33.3%), unknown 1 (33.3%)
- **Readiness basis unknown fraction:** 33.3%

## Censoring and exclusions

- Open pull requests: 1 (33.3%)
- Unmerged pull requests: 2 (66.7%)
- Excluded from lifecycle fitting: 2 (66.7%)
- Exclusion reasons: reopened: 1, unknown_readiness: 1

## Missingness

| Collection family | Field | Missing | Fraction |
|---|---|---:|---:|
| `pull_requests` | author | 1 | 33.3% |
| `pull_requests` | draft_status | 1 | 33.3% |
| `pull_requests` | merge_time | 2 | 66.7% |
| `pull_requests` | size | 3 | 100.0% |
| `reviews` | author | 1 | 100.0% |
| `reviews` | submission_time | 1 | 100.0% |
| `reviews` | revision | 1 | 100.0% |
| `lifecycle_events` | actor | 2 | 100.0% |
| `lifecycle_events` | revision | 2 | 100.0% |
| `ci_observations` | start_time | 0 | n/a |
| `ci_observations` | completion_time | 0 | n/a |
| `ci_observations` | revision | 0 | n/a |
| `derived_features` | ready_time | 1 | 33.3% |

## Extraction limitations

- Snapshot reconciliation is not a point-in-time GitHub transaction.
- GitHub activity Events are not used as an archive; only allowlisted issue lifecycle events are retained.
- Unknown readiness is excluded from ready-based calibration rather than replaced with zero draft time.
- Partial and unavailable endpoint collections are incomplete evidence and must not be interpreted as empty, complete history.
- Not-requested endpoint collections provide no evidence for that collection family.
