# OpenCode in Amp orbs

OpenCode is an optional repository development tool. It does not change the
merge-carlo package, CLI, simulation, or network boundaries.

## Setup and authentication

`mise run setup` installs the version pinned in `mise.toml` and `mise.lock`.
OpenCode's own updater is disabled so the binary remains reproducible. Warm
setup lets mise verify the existing binary and does not download it again.

The project uses OpenCode's built-in `zai-coding-plan` provider and its OpenAI
Chat Completions-compatible Coding Plan endpoint:

```text
https://api.z.ai/api/coding/paas/v4
```

Authentication is HTTP Bearer through the provider's supported
`ZHIPU_API_KEY` environment variable. Amp supplies the user-configured,
project-scoped `ZAI_API_KEY`; `scripts/opencode` maps it to `ZHIPU_API_KEY` only
in the launched process and removes the original variable. The skill-inventory
subprocess receives neither credential variable. The key is never written to
OpenCode auth storage or repository files. Do not run
`opencode auth login`, enable `--print-logs`, echo either key variable, or add
them to shell profiles.

Each provider request has a 15-minute total timeout. OpenCode also applies its
own header and between-chunk deadlines. The total bound prevents a stream that
continues producing chunks from running indefinitely; a multi-turn agent run
may make more than one independently bounded request.

Always invoke OpenCode through the repository launcher, including when an Amp
agent is prompted to use OpenCode:

```bash
scripts/opencode --profile glm-5.3-max run "Implement the requested change and run the checks."
```

The launcher also refreshes private skills before every invocation. Calling the
`opencode` binary directly bypasses the secret bridge and that refresh.

## Models and reasoning profiles

As of OpenCode 1.18.30 and the Z.AI documentation checked on 2026-09-11, both
models always reason and expose exactly `low`, `high`, and `max`. They do not
expose `none`, `medium`, `extra-high`, or `xhigh`.

| Profile | OpenCode model | Z.AI `reasoning_effort` | Use |
|---|---|---|---|
| `glm-5.3-low` | `zai-coding-plan/glm-5.3` | `low` | Small, direct edits |
| `glm-5.3-high` | `zai-coding-plan/glm-5.3` | `high` | Normal implementation |
| `glm-5.3-max` | `zai-coding-plan/glm-5.3` | `max` | Complex or high-risk work |
| `glm-5.3-flash-low` | `zai-coding-plan/glm-5.3-flash` | `low` | Fast, lightweight work |
| `glm-5.3-flash-high` | `zai-coding-plan/glm-5.3-flash` | `high` | Normal fast-model work |
| `glm-5.3-flash-max` | `zai-coding-plan/glm-5.3-flash` | `max` | Deeper fast-model work |

The project default is `glm-5.3-max`; GLM-5.3-Flash is the small model. A later
agent should translate an explicit user request to the matching profile. With
no requested model or effort, use `glm-5.3-max`. If the user asks for an
unsupported `medium`, use `high` and state the fallback. If the user asks for
unsupported `extra-high` or `xhigh`, use `max` and state the fallback. Never
claim that a fallback is the requested native level.

For models added after these profiles, use native OpenCode selection without a
source change:

```bash
scripts/opencode run \
  --model zai-coding-plan/FUTURE_MODEL_ID \
  --variant FUTURE_SUPPORTED_VARIANT \
  "Prompt"
```

First confirm the model and variant with current Z.AI and OpenCode docs. To
change the repository defaults, update `model`, `small_model`, and the `build`
and `plan` agent settings in `opencode.json`; profile aliases remain deliberately
limited to combinations verified by the deterministic setup test.

## Private Amp User Skills

OpenCode directly understands the same `<name>/SKILL.md` format used by Amp,
but Amp's signed-in global User Skills are materialized in a private cache whose
versioned directories are not among OpenCode's discovery paths. Amp does not
currently provide a command that installs that private inventory directly into
OpenCode.

`.agents/resume` and `scripts/opencode` therefore run
`scripts/sync-opencode-skills.py`. It asks the authenticated Amp CLI for
`global-user` skill metadata and creates directory symlinks under
`~/.config/opencode/skills/`. Skill files stay in Amp's read-only private cache;
they are never copied, adapted, printed, or placed in this repository. A
private, mode-0600 manifest under
`~/.local/state/merge-carlo/opencode-user-skill-links.json` permits safe stale
link cleanup. Existing user-managed OpenCode skill paths are never overwritten.
Relative `XDG_CONFIG_HOME` or `XDG_STATE_HOME` values are rejected so links and
the private manifest cannot accidentally land in the worktree. Absolute paths
that resolve inside the repository are rejected for the same reason.

Refresh occurs on orb resume and before every launcher invocation. Run the
following manually after changing the private User Skills repository:

```bash
python3 scripts/sync-opencode-skills.py
```

If `amp skill list --json` is unavailable, the CLI is not authenticated, or a
skill has not materialized, resume emits a generic warning and defers. The
launcher fails closed instead of starting OpenCode without the requested private
skills. Start a fresh Amp orb/session or restore Amp authentication, then retry.
No repository fallback copies private content.

## Troubleshooting and validation

- `ZAI_API_KEY is unavailable`: confirm the project-scoped secret exists and
  start a fresh orb so its environment is refreshed. Never paste the value into
  a command, file, issue, or log.
- `OpenCode is unavailable`: run `mise run setup`.
- Skill sync reports a collision: move or remove the conflicting user-managed
  path under `~/.config/opencode/skills/`; the adapter will not overwrite it.
- Inspect public configuration with `opencode debug config`, but do not add
  `--print-logs` while authenticated.
- Run `bash scripts/check-opencode-setup-test.sh` for deterministic pin,
  profile, argument pass-through, secret-redaction, symlink, and repository
  privacy checks.

Current upstream references:

- [Z.AI OpenCode integration](https://docs.z.ai/devpack/tool/opencode)
- [Z.AI Coding Plan endpoints](https://docs.z.ai/devpack/tool/others)
- [GLM-5.3 reasoning levels](https://docs.z.ai/guides/llm/glm-5.3)
- [GLM-5.3-Flash](https://docs.z.ai/guides/vlm/glm-5.3-flash)
- [OpenCode models and variants](https://opencode.ai/docs/models)
- [OpenCode skill format and discovery](https://opencode.ai/docs/skills)
