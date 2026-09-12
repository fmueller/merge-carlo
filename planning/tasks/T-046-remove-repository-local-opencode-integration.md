---
id: T-046-remove-repository-local-opencode-integration
title: Remove repository-local OpenCode integration
status: completed
priority: high
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-12T14:07:48Z"
---

# T-046-remove-repository-local-opencode-integration Remove repository-local OpenCode integration

## Description

Remove the repository-local OpenCode integration superseded by the optional
private global `/opencode` User Skill. Preserve simulator behavior and all
unrelated setup, CI, toolchain, and tracked work.

## Acceptance

- Remove project configuration, launcher, skill sync, tool pins, and their CI
  checks; resume works without tools, credentials, or network access.
- Document personal tooling ownership without publishing private skill content,
  inventory, credentials, or runtime state.
- Validate real GLM-5.3/high and GLM-5.3-Flash/max inference through the global
  skill from a fresh orb and confirm private runtime discovery and no leakage.
- Setup remains fast and idempotent; full repository and workflow checks pass.
- Review the cleanup independently, push to main, and confirm settled CI.

## Verification Notes

- Resume regression test first failed against runtime synchronization, then
  passed after restoring the no-op. It runs with an empty environment and no
  external commands on PATH.
- `mise run check`: ruff, formatting, mypy, 657 tests, and all remaining guard
  suites passed. `actionlint` 1.7.12 validated all GitHub workflows.
- `.agents/setup` completed in 1.05 seconds and its warm rerun in 0.69 seconds;
  `.agents/resume` completed in under 0.01 seconds. A clean login shell could
  invoke all three pinned tools through `mise exec`.
- From this fresh orb's repository cwd, the private global skill ran real
  GLM-5.3/high and GLM-5.3-Flash/max requests successfully. Both reported runtime
  skill availability without listing inventory and answered arithmetic checks
  correctly. These checks were repeated with the final published global skill,
  including its newest-retained-cache-revision selection fix. Diagnostics,
  refresh, and all 15 private launcher tests passed with that revision.
- Live process inspection confirmed environment-only credential mapping and
  in-memory configuration with skill paths outside the worktree. Scans of
  captured output, private runtime files, tracked files, and non-cache worktree
  files found no credential value. Tracked-file checks found no copied personal
  skill files or generated private runtime paths.
- Independent read-only OpenCode review found no security or correctness defects.
  It requested complete verification notes; the setup, full-check, inference,
  and privacy evidence above resolves that documentation gap. A fresh independent
  disposition review confirmed the finding resolved.
- The phase-1 publisher confirmed that the loaded launcher's content hash
  matches the final published private global skill baseline.
- The [cleanup commit](https://github.com/fmueller/merge-carlo/commit/283fc0800f07b8c7f6b329af725957977a26cd9c)
  was pushed directly to main and its remote SHA confirmed. Both
  [Build](https://github.com/fmueller/merge-carlo/actions/runs/34698246504)
  (including Python 3.12, 3.13, and 3.14) and
  [CodeQL](https://github.com/fmueller/merge-carlo/actions/runs/34698246195)
  completed successfully. No cleanup-caused CI fixes were needed.

## Implementation Notes

- Preserve T-045 as explicitly superseded historical evidence; do not rewrite
  its machine-managed completion state.
- The fetched main branch matched the original integration commit, with no
  later changes to reconcile. The simulator, dependency lock, setup bootstrap,
  hook policy, and unrelated workflow behavior remain unchanged.
- 2026-09-12T14:03:31Z: verification pass
- 2026-09-12T14:07:48Z: verification pass
- 2026-09-12T14:07:48Z: Removed repository-local OpenCode; final global replacement and successful main CI verified.
