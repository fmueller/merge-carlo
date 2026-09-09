# AGENTS.md

Guidance for coding agents working in the merge-carlo repository.

## Scope and intent

- merge-carlo is a local, read-only, offline-first simulator of pull-request
  review workflows. It makes no LLM calls and takes no GitHub write action.
- The active spec in `specs/` is the v0.1.0 scope boundary. Work outside it
  needs a spec change first, not a larger diff.
- Keep changes small and cohesive. Do not scaffold roadmap architecture without
  an active requirement; a module lands with the milestone that needs it.
- A specification, interface sketch, or TODO is not an implemented feature. If a
  requirement cannot be completed, preserve the working slice and state the exact
  missing behavior rather than leaving a success-shaped stub.

## Source of truth

- `specs/` holds the versioned specs that are normative for the model, the
  command contract, the metric definitions, and the explicit non-goals. The
  active spec is named in `planning/STATE.md`.
- `docs/limitations.md` records what the model cannot establish; keep it current
  as milestones land.
- `planning/tasks/` holds one file per tracked task, each linked to a spec
  heading through `spec_ref`.
- `pyproject.toml` defines the dependency set, lint, type, and test configuration.
- `mise.toml` pins the developer and CI toolchain; `mise run check` is the local
  gate and mirrors the CI `Build` workflow.
- `lefthook.yml` and `scripts/check-*.sh` define the commit policy. The guards
  carry their own `*-test.sh` suites, which run in pre-commit and in CI.

## Architecture boundaries

- The simulation package must not import the GitHub client and must not make
  network requests. Ingestion depends on nothing above it.
- Reporting reads result artifacts. It must never rerun a simulation.
- Dataset content hashes cover normalized records and canonical JSON, not the
  physical bytes of a SQLite file.
- Never sample an observed elapsed review delay and treat it as active review
  effort. Elapsed delay and active service are different quantities; conflating
  them double-counts queueing. The mechanistic model consumes an assumed effort
  distribution; the elapsed-delay benchmark is a separate model.
- Every model parameter carries a provenance basis: `observed`, `derived`,
  `proxy`, `assumed`, or `synthetic`. Demonstration numbers are synthetic and
  must never be presented as measured team behavior.
- A bot account is not an AI coding agent, and a human account can submit
  AI-assisted work. `unknown` origin is a valid result, never guessed.
- Serialize artifacts through versioned contracts. Do not pickle objects.
- Do not add a dependency until an implemented requirement needs it. No
  unbounded `latest` pins. Pandas, SciPy, an ORM, a charting stack, a database
  server, and a frontend are out of scope.

## Toolchain and commands

- Setup: `mise run setup` (pinned tools, `uv sync --locked --dev`, `lefthook install`).
- Full local gate: `mise run check`; it mirrors the CI checks step for step.
- Lint: `uv run ruff check` (`--fix` to autofix). Format: `uv run ruff format`.
- Type check: `uv run mypy` (reads its file set from `pyproject.toml`; no path argument).
- Tests: `uv run pytest`; a single file with `uv run pytest tests/unit/cli_test.py`.
- Run the CLI: `uv run merge-carlo --help`.

Always run ruff, mypy, and pytest at the end of a task and fix what they report.

## Python conventions

- Python 3.12 is the supported floor and what mypy checks; 3.13 is the reference
  version in `.python-version`; CI also tests 3.14.
- Ruff: 120-character lines, double quotes, 4-space indent, import sorting.
- Mypy runs strict. Every function is fully typed.
- Prefer `TypedDict`, `Protocol`, dataclasses, or Pydantic v2 models over loose
  dictionaries. Configuration models reject unknown keys.
- Load YAML safely. No configuration value may execute Python, import a class,
  evaluate an expression, or invoke a shell command.
- Use parameterized SQL, bounded HTTP and JSON sizes, and no shell interpolation.
- Redact authorization headers in every diagnostic. Tokens never reach a dataset,
  a resolved configuration, an exception body, a trace, or a report.
- Source lives in `src/merge_carlo/`; tests mirror module names as
  `tests/unit/<module>_test.py`.

## Testing

- Tests are marked `unit`, `integration`, or `property`.
- Ingestion tests use saved synthetic HTTP fixtures. Never call live GitHub in
  normal CI. A live smoke test needs an explicit flag, supplied credentials, and
  one selected permitted repository, and must not enumerate anything else.
- Property tests use Hypothesis for the model invariants:
  conservation of pull requests, no self-review, no stale-revision approval, no
  terminal-state revival, utilization never above one, and reproducibility under
  a fixed seed.
- Assert that bodies, patches, tokens, and email addresses never appear in
  stored projections or logs.

## Taskrail lifecycle

Planning and task state live in the repository and are managed by the `taskrail`
CLI.

```bash
taskrail status                 # current snapshot (read-only)
taskrail next                   # deterministic next eligible task
taskrail start <task-id>        # mark active
taskrail complete <task-id>     # mark implemented
taskrail verify <task-id> --result pass|fail --summary "..."
taskrail block <task-id> --reason "..."
taskrail validate               # structure and spec references
taskrail coverage               # spec coverage, orphans, drift
```

- `planning/STATE.md` is generated execution state, not a log. Never hand-edit
  it, and never append continuation prose; mechanical drift is fixed with
  `taskrail repair --apply`.
- Never hand-edit a task `status:` or any machine-managed field. If no command
  expresses the change you need, that is a missing capability: file a task.
- New work needs a task (`taskrail task new --title ... --area <spec-anchor>`)
  so no change bypasses a spec heading.
- A task must be one independently meaningful outcome with a bounded
  implementation and verification surface. Never split by file, layer,
  discipline, phase, or estimate.
- Run `git status` after every state-writing command.
- The packaged tracked-work skills are installed at `.claude/skills/` and
  `.agents/skills/`. The two trees are byte-identical mirrors: reinstall with
  `taskrail init --with-skills --force` rather than editing one copy, and never
  let them drift apart.

## Changes and commits

- Prefer small, cohesive changes that preserve clear package ownership.
- Update `CHANGELOG.md` under `## [Unreleased]` for user-visible behavior
  changes, in the same commit as the change.
- Coding agents must run `mise run setup` (or `lefthook install`) before creating
  their first commit in a worktree; do not assume the hooks are already installed.
- Use Conventional Commits with imperative subjects. Types: `feat fix refactor
  docs test chore build perf ci`.
- Never add attribution trailers: no co-authorship line, no agent session or
  thread trailer, and no session link. `scripts/check-attribution.sh` is the one
  policy the `commit-msg` and `pre-push` hooks both apply.
- Commit under the maintainer's git identity. `scripts/check-author.sh` refuses
  an agent author in `pre-commit` and again in `pre-push`, so an agent runner
  must set `user.name` and `user.email` before its first commit.
- Include a descriptive body after the subject, wrap body lines at 72 characters,
  and suffix tracked-task subjects with the short key, for example `(T-001)`.
- Keep tracked tasks focused and include objective verification evidence.
- Do not mix unrelated refactors or formatting churn into feature changes.
- Do not rewrite shared history or bypass CI-equivalent checks.
- Update public documentation when user-visible behavior or setup changes.
- Do not push, publish a package, create a release, or modify repository
  governance unless separately requested.

## Language rules for generated output

Reports are deterministic templates. They may state that a scenario's direction
is consistent across the tested assumption sets. They may not claim a
productivity gain, name an underperforming developer, declare an auto-approval
threshold safe, or predict an exact future backlog. `defect_escape_rate`,
`security_risk_change`, and `policy_safety` are `null` with an
`unsupported_in_v0_1` reason.
