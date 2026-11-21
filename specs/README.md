# Specs

This repository uses versioned specs under `specs/`.

- `specs/v0.1.0.md` is the active spec and the scope boundary for the first
  release. Tracked work in `planning/tasks/` links to its headings.
- `specs/v0.2.0.md` is an inactive draft that holds work deferred from v0.1.0.
  It adds an optional merge queue and the trunk-based integration core, which
  compares direct-to-trunk integration with short-lived and longer-lived
  pull-request branches through a delivery pipeline to production.
- `specs/v0.3.0.md` is an inactive draft that extends the v0.2.0 trunk-based
  core with feature activation, further non-blocking review policies,
  follow-up work, and professional workflow profiles.
- `specs/v0.4.0.md` is an inactive draft for shared CI and deployment capacity,
  deployment environments, trunk breakage, rollback, and staged rollouts.

## Reading Order

1. `specs/v0.1.0.md`
2. `specs/v0.2.0.md`
3. `specs/v0.3.0.md`
4. `specs/v0.4.0.md`
