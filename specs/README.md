# Specs

This repository uses versioned specs under `specs/`.

- `specs/v0.1.0.md` is the scope of the first release, published as v0.1.1.
- `specs/v0.2.0.md` is the active spec and the scope boundary for the next
  release. Tracked work in `planning/tasks/` links to its headings. It holds
  work deferred from v0.1.0.
  It adds an optional merge queue and the trunk-based integration core, which
  compares direct-to-trunk integration with short-lived and longer-lived
  pull-request branches through a delivery pipeline to production.
- `specs/v0.3.0.md` is an inactive draft that extends the v0.2.0 trunk-based
  core with feature activation, increment size, stacked pull requests,
  size-based review eligibility, further non-blocking review policies,
  follow-up work, and professional workflow profiles.
- `specs/v0.4.0.md` is an inactive draft for shared CI and deployment capacity,
  size-dependent build time, deployment environments, trunk breakage, rollback,
  and staged rollouts.
- `specs/v0.5.0.md` is an inactive draft for latent defect introduction,
  detection, escape, and remediation, which gives review and size-based
  eligibility comparisons a modeled quality cost.

## Reading Order

1. `specs/v0.1.0.md`
2. `specs/v0.2.0.md`
3. `specs/v0.3.0.md`
4. `specs/v0.4.0.md`
5. `specs/v0.5.0.md`
