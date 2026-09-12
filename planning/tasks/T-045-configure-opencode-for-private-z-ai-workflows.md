---
id: T-045-configure-opencode-for-private-z-ai-workflows
title: Configure OpenCode for private Z.AI workflows
status: completed
priority: medium
spec_ref: specs/v0.2.0.md#tracked-work-tooling
dependencies: []
updated_at: "2026-09-11T23:24:44Z"
---

# T-045-configure-opencode-for-private-z-ai-workflows Configure OpenCode for private Z.AI workflows

> Historical implementation and verification record. Superseded by T-046:
> OpenCode now belongs to the optional private global `/opencode` User Skill,
> not repository setup or CI. The commands and pins below describe the original
> implementation and are no longer current contributor instructions.

## Description

Install and configure OpenCode reproducibly for the Z.AI Coding Plan without
changing merge-carlo product behavior. Bridge the project-scoped secret only at
runtime and expose Amp's private User Skills through non-repository links.

## Acceptance

- OpenCode is version-pinned in the existing mise toolchain and warm setup stays
  idempotent.
- The built-in Z.AI Coding Plan provider uses the project secret without writing
  its value to configuration, files, or logs.
- GLM-5.3 and GLM-5.3-Flash have documented low, high, and max profiles, while
  native model and variant flags remain available for future models.
- A runtime adapter exposes all Amp `global-user` skills to OpenCode without
  copying private contents or inventory into Git-tracked files.
- Deterministic setup/privacy checks and real inference smoke tests validate the
  supported profiles.

## Verification Notes

- `mise run check`: ruff, format, mypy, 657 tests, and all repository guards
  passed.
- `bash scripts/check-opencode-setup-test.sh`: pin, configuration, profile,
  secret-boundary, symlink-safety, and repository-privacy checks passed.
- Real `scripts/opencode --profile <name> run` inference returned `OK` for all
  six documented profiles; captured output and OpenCode runtime logs/state did
  not contain the credential.
- `.agents/setup` completed in 1.07 seconds and a warm rerun in 0.72 seconds;
  `.agents/resume` completed in 1.66 seconds.

## Implementation Notes

- OpenCode 1.18.30 is locked through mise and uses the built-in
  `zai-coding-plan` provider with its Coding Plan endpoint.
- The launcher maps `ZAI_API_KEY` to the provider's supported environment name
  only for OpenCode and strips both credential variables from skill discovery.
- Amp `global-user` skills remain in the private runtime cache and are exposed
  through user-config symlinks; no private skill contents or inventory are
  stored in the repository.
- 2026-09-11T23:24:44Z: verification pass
