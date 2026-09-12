# Contributing

Thanks for your interest in merge-carlo.

**Coding agents / AI tools:** [`AGENTS.md`](AGENTS.md) is authoritative; read it first.

| Topic | Where |
| --- | --- |
| Scope and model rules | the active spec in `specs/` |
| Agent and contributor rules | [`AGENTS.md`](AGENTS.md) |
| Tracked work | `planning/STATE.md` and `planning/tasks/` |
| Known limitations | [`docs/limitations.md`](docs/limitations.md) |

## AI-assisted contributions

AI-generated and AI-assisted pull requests are welcome. Two rules apply:

1. **You own the diff.** Whoever opens the pull request is accountable for every
   line, whether written by a human or a tool.
2. **No bot attribution.** Do not add `Co-Authored-By: <bot>`, `Assisted-By:`,
   `Generated with ...`, agent session or thread trailers such as
   `Claude-Session:` or `Amp-Thread:`, links to an agent session, or 🤖 trailers.
   The `commit-msg` hook rejects them and the `pre-push` hook rescans the
   outgoing commits, so a message that skipped the first gate is still caught
   before it reaches the remote. Commit as yourself, too: a commit authored by an
   agent identity such as `Claude <noreply@anthropic.com>` is refused by the
   `pre-commit` and `pre-push` hooks, because the author header makes the same
   claim the trailers do. The AI is a tool, not a co-author.

The same quality gate applies regardless of how the code was produced.

## Setup

```bash
mise run setup
```

That installs the pinned toolchain, syncs the locked dependencies, and installs
the git hooks. The hooks are opt-in, so a fresh clone has none until you run it.

Without mise:

```bash
uv sync --locked --dev
lefthook install
```

OpenCode is optional personal tooling, not a repository dependency. Amp users
with the private global `/opencode` User Skill can invoke it from this checkout;
the skill owns installation, configuration, authentication, and runtime skill
discovery. Repository setup, resume, and CI do not install or invoke OpenCode.
Do not copy personal skills, credentials, or generated runtime state into the
repository. Contributors without that private skill need only the setup above.

## Before you open a pull request

- Run `mise run check`. It mirrors the CI checks step for step.
- Use a Conventional Commit subject. Types: `feat fix refactor docs test chore
  build perf ci`. End tracked-task subjects with only the short key, for example
  `feat: add the review duty calendar (T-004)`. Never a task prefix or the full
  slugged identifier; non-tracked commits may omit the reference.
- After the subject and a blank line, include a concise body explaining the
  commit's intent, context, and non-obvious decisions rather than restating the
  diff. Wrap body lines at 72 characters.
- Update `CHANGELOG.md` under `## [Unreleased]` for user-visible changes.
- Keep unrelated refactors and formatting churn out of feature changes.

## Continuous integration

The `Build` workflow runs lint, formatting, and type checks, then the commit
policy guard suites, then the test suite on Python 3.12, 3.13, and 3.14. The
hooks are local and opt-in, so CI is the backstop for the commit policy.

The `Mutation tests` workflow runs the full mutation gate weekly and on manual
dispatch, never on a pull request: mutmut re-runs the suite once per mutant. For
a logic-heavy change, run `mise run test:mutate` locally instead — it mutates
only the modules your change touched.

The [v0.1.0 mutation policy](docs/mutation-policy.md) sets the per-module floor
to 80% (previously 90%), with the existing ten-mutant minimum. Raw counts and
survivors remain visible and unadjusted. Reassess this explicitly version-scoped
threshold before adopting it for a later release.

## Tracked work

Work is tracked with the `taskrail` CLI. Every change should map to a task whose
`spec_ref` resolves to a heading in the active spec. `planning/STATE.md` is
generated; do not hand-edit it.

## Scope

merge-carlo is a local, read-only, offline-first simulator. It makes no LLM
calls, takes no GitHub write action, ingests no source code, and ships no web
service. Proposals outside that boundary need a spec change before code.

## License

By contributing you agree that your contributions are licensed under the
Apache License 2.0, as in [`LICENSE`](LICENSE).
