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
T-030 (release mutation validation) also remains applicable to v0.1.0. T-033
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
