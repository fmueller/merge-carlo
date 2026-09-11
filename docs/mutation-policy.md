# Mutation gate policy for v0.1.0

On 2026-09-10 the maintainer explicitly selected an **80% per-module mutation
efficacy floor for v0.1.0**, replacing 90%. This is a deliberate relaxation of
the acceptance threshold, not an improvement in measured test efficacy. It is
not a standing policy for later releases: reassess the default when changing
the active spec beyond v0.1.0.

`scripts/check-mutation-floor.sh` owns the default. Differential runs, the full
local gate, and the weekly CI gate use that same guard. Its existing `--floor`
option remains available for explicit comparisons; an overridden run must
report the threshold used and must not be presented as the default gate.

Everything else remains unchanged:

- Report raw per-module killed-or-timeout counts, total counts, percentages,
  and below-floor failures. The numerator retains the existing timeout
  convention. Do not remove equivalent survivors from the denominator or
  relabel them as killed.
- Evaluate modules independently; a strong module cannot mask a weak one.
- Fewer than ten mutants means insufficient evidence, not an efficacy verdict.
- Keep raw mutation outcomes and command failures visible in logs and artifacts.
  The weekly workflow still collects and uploads raw results before enforcing
  the floor. A lower threshold does not excuse tool failures or missing runs.
- Record genuinely equivalent mutants with reasons rather than silencing them.
  Do not write tests solely to distinguish default-preserving mutations.

The previously proposed manual-equivalence exception was not shipped and is
not part of this policy. No allowlist, adjusted score, or manual override is
introduced.

## Differential scope

`mise run test:mutate` evaluates only the exact modules selected by its diff.
The guard accepts repeated `--module <dotted-name>` arguments; without them,
the full gate still evaluates every discovered module independently. Unrelated
cached results cannot fail or inflate a differential verdict. Missing selected
results or selected `not checked` mutants fail, even below ten mutants.
Completed small samples still report insufficient evidence. Counts and survivor
denominators are unchanged; `uv run mutmut results --all true` retains all raw
outcomes, including unrelated modules.

## T-005 and remaining release work

T-005 reported 34/39 = 87.2%. Those same raw counts fail at 90% and pass at 80%,
with all five survivors still counted. T-035 verifies that decision using a
synthetic shell fixture, not by importing or rerunning T-005's isolated code.
The T-005 owner must reconcile this policy and rerun its actual verification;
the old failed run must not be rewritten as a historical pass.

T-035 removes T-005's numerical-floor blocker. T-034 resolves the separate
differential accounting problem described above. T-005 must reconcile both
changes and rerun its actual verification before claiming a clean gate.
T-030 (release mutation validation) records its evidence under "Release
mutation gate (T-030)" below. T-033
(dataclass mutation discovery) is deferred to v0.2.0: mutmut 3.7.0 skips
decorated class bodies, so v0.1.0 per-module scores do not cover `@dataclass`
methods. None is implemented by T-035.

## Discovery limitations in v0.1.0

The pinned mutmut 3.7.0 does not generate mutants for every function. A
per-module score describes only the functions mutmut instruments; code it skips
is not mutation-covered, whatever that module's percentage. Skipped functions
never enter the denominator, so nothing is excluded after the fact, and
production code is not restructured to suit the tool.

- Decorated functions and methods are skipped, except a lone `@staticmethod` or
  `@classmethod`. Upstream main still skips them (boxed/mutmut#387 is open).
  In v0.1.0 this leaves out:
  - Pydantic `@model_validator` and `@field_validator` methods, including the
    artifact validators `Probability.check_probability` and
    `Summary.check_summaries` in `merge_carlo.reporting` (T-040), and the
    validators in `configuration`, `calibration`, `inspection`, `store`, and
    `validation`;
  - the Typer `@app.callback` and every `@app.command` body in
    `merge_carlo.cli`: `schema`, `demo`, `collect`, `inspect`, and `validate`
    (T-041);
  - `@property` methods such as `UTCInterval.seconds` and
    `PullRequest.terminal`.
- Methods of decorated classes, including every `@dataclass` body, are skipped.
  That discovery work (T-033) is deferred to v0.2.0.

The scoped alternative for T-040 and T-041 is behavioral testing, not a
mutation score:

- `tests/unit/reporting_test.py` rejects invalid probability counts and bounds,
  zero-trial probabilities with defined values or bounds, denominator
  mismatches, nonfinite or unordered quantiles, inconsistent replication totals,
  and inconsistent null values or reasons.
- `tests/unit/cli_test.py` and `tests/integration/demo_test.py` cover option
  forwarding, exit codes `2`, `3`, and `4`, a demo that uses no credentials,
  HTTP client, or socket, SYNTHETIC output labeling, and preservation of
  existing output.

Scoped run on 2026-09-11, before the two added reporting tests:
`uv run mutmut run "merge_carlo.reporting.*" "merge_carlo.cli.*"` took 12.8 s
of wall time, and the guard reported both modules above the 80% floor.

| Module | Killed/total | Verdict | Mutated functions |
| --- | --- | --- | --- |
| `merge_carlo.reporting` | 231/243 (95.1%) | ok | `markdown`, `_number`, `_probability`, `_range`, `render_report`, `wilson` |
| `merge_carlo.cli` | 74/90 (82.2%) | ok | `_emit`, `_print_version`, `JsonTyperGroup.main` |

Neither score covers the validators or command bodies listed above.

## Release mutation gate (T-030)

The release gate is the full `mise run test:mutate:gate`: every discovered module,
the default 80% floor, and no module or survivor excluded. The engine
(`merge_carlo.simulation.engine`), scenario runner
(`merge_carlo.simulation.runner`), and metric (`merge_carlo.simulation.metrics`)
modules are the logic-heavy modules this gate must hold on; their scores cover
only discovered functions, so the dataclass and `@property` limitations above
still apply.

### Per-module result

`mise run test:mutate:gate` passed on 2026-09-11 with the tests below, starting
from an empty `mutants/` cache (382 s wall time, 32 workers). Every module clears
the 80% floor; counts are raw killed-or-timeout over all discovered mutants.

| Module | Killed/total | Verdict |
| --- | --- | --- |
| `merge_carlo.artifacts` | 494/579 (85.3%) | ok |
| `merge_carlo.attribution` | 166/188 (88.3%) | ok |
| `merge_carlo.benchmark` | 206/241 (85.5%) | ok |
| `merge_carlo.calibration` | 612/684 (89.5%) | ok |
| `merge_carlo.cli` | 74/90 (82.2%) | ok |
| `merge_carlo.cohort` | 279/323 (86.4%) | ok |
| `merge_carlo.configuration` | 98/120 (81.7%) | ok |
| `merge_carlo.demo` | 221/225 (98.2%) | ok |
| `merge_carlo.features` | 637/781 (81.6%) | ok |
| `merge_carlo.github` | 450/537 (83.8%) | ok |
| `merge_carlo.inspection` | 672/818 (82.2%) | ok |
| `merge_carlo.reporting` | 231/243 (95.1%) | ok |
| `merge_carlo.simulation.arrivals` | 134/142 (94.4%) | ok |
| `merge_carlo.simulation.bypass` | 53/55 (96.4%) | ok |
| `merge_carlo.simulation.calendars` | 59/61 (96.7%) | ok |
| `merge_carlo.simulation.capacity` | 37/40 (92.5%) | ok |
| `merge_carlo.simulation.engine` | 601/613 (98.0%) | ok |
| `merge_carlo.simulation.metrics` | 278/285 (97.5%) | ok |
| `merge_carlo.simulation.randomness` | 34/39 (87.2%) | ok |
| `merge_carlo.simulation.runner` | 172/176 (97.7%) | ok |
| `merge_carlo.store` | 364/440 (82.7%) | ok |
| `merge_carlo.validation` | 981/1192 (82.3%) | ok |

Before the tests below, the engine scored 598/613 (97.6%) and the metrics module
277/285 (97.2%). The weekly GitHub workflow run of this gate has not been
observed for this change.

### Surviving mutants in the engine, runner, and metric modules

The first full run left 27 survivors in these three modules. Four exposed
unpinned model behavior and are now killed by behavioral tests:

- `metrics` `Measurement.finish` mutant 44 excluded a first review completed
  exactly at the measurement start from first-review latency. The window is
  half-open and includes its start:
  `test_first_review_completed_exactly_at_window_start_is_measured`.
- `engine` `run_fifo` mutant 235 counted a draw equal to the requested-change
  probability as a measured requested change while the lifecycle approved it:
  `test_probability_threshold_is_exclusive_and_random_defaults_are_zero` now
  asserts the measured count agrees with the lifecycle.
- `engine` `run_fifo` mutants 278 and 291 made the bypass eligibility and audit
  thresholds inclusive, so a fraction of zero could still bypass or audit:
  `test_bypass_fraction_thresholds_are_exclusive`.

The remaining survivors stay in the denominator. Equivalent mutants cannot be
distinguished through any reachable engine state:

| Module | Mutants | Change | Why no test can distinguish it |
| --- | --- | --- | --- |
| `metrics` | `Measurement.completed_review` 7; `Measurement.finish` 5, 20, 28, 45 | `< window.end` becomes `<=` | The measurement end must equal the horizon, and the horizon step only censors: no review completes, no proposal is admitted, and nothing merges or is abandoned at the horizon. |
| `metrics` | `Measurement.finish` 11 | `terminal_at is None or censored` becomes `and` | The horizon step gives every nonterminal proposal a terminal time and truncated runs produce no metrics, so no proposal reaches `finish` without one. |
| `metrics` | `Measurement.finish` 159 | `share(False)` becomes `share(None)` | Both are falsy and take the merged-share branch. |
| `engine` | `run_fifo` 99 | a duty interval ending at the run start is kept | It is clipped to a zero-length interval that adds no duty, dispatch, or eligibility. |
| `engine` | `run_fifo` 106, 139, 334 | arrivals, scheduled loop events, and deadlines at the horizon are queued | The horizon step only censors, so queued work at the horizon is never processed. |
| `engine` | `run_fifo` 152 | the first step starts from `previous = 1` | The first step is at time zero with no assignment, and its measured duration clips to zero. |
| `runner` | `ExperimentRun.__init__` 2 | `_exhausted = None` | It is only read through `not`, where `None` and `False` agree. |

The other survivors change only an error message: `engine` `run_fifo` 10, 21,
29, 37, 43, 47, and 69 wrap the text in `XX`, and `runner` `_unique` 5, 6, and 7
drop, wrap, or upper-case it. They are not equivalent, but the tests assert the
error type and a stable message fragment rather than exact text, so no test is
added only to pin the wording.

Three `engine` `run_fifo` mutants (145, 210, and 451) time out because they stop
the scheduler from making progress. Under the existing timeout convention they
count as killed.

### Runtime

Measured on 2026-09-11 with mutmut 3.7.0 on an AMD Ryzen 9 5950X (16 cores, 32
threads), starting each run from an empty `mutants/` cache. Every run generated
7,872 mutants across 25 files.

| Run | Workers | Wall time |
| --- | --- | --- |
| Full gate, `uv run mutmut run` | 32 (default) | 383 s |
| Full gate, `uv run mutmut run --max-children 4` | 4 | 894 s |
| Differential, `scripts/mutate-diff.sh` after an `engine.py`-only change | 32 (default) | 224 s |

The four-worker run matches the vCPU count of a GitHub-hosted `ubuntu-latest`
runner. It overlapped briefly with a smaller scoped run, so it slightly
overstates the time. Its 894 s is about a sixth of the workflow's 90-minute
timeout, so the timeout and the scheduled command are unchanged. A hosted
runner's cores are slower, so this is a local estimate, not a measured CI
runtime. The differential run selected only `merge_carlo.simulation.engine`.
From a cold cache it first collects test coverage across the whole suite; later
runs reuse that cache. Timeout outcomes vary slightly between runs (14 against
13 above) because they depend on machine load.
