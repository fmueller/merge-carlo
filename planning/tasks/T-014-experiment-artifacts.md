---
id: T-014-experiment-artifacts
title: Write experiment artifacts and the deterministic report
status: completed
priority: high
spec_ref: specs/v0.1.0.md#experiment-runner-and-reporting
dependencies:
    - T-013-metric-dictionary
updated_at: "2026-09-10T17:04:18Z"
---

# T-014-experiment-artifacts Write experiment artifacts and the deterministic report

## Description

Write the experiment artifacts and render the report: manifest, resolved
scenarios, model card, summary JSON and CSV, paired deltas, replication rows, a
Markdown report, and sampled traces. The report is a deterministic template.
Reporting reads artifacts and never reruns a simulation.

## Acceptance

- The report follows the required order: question and evidence status, scenario comparison, uncertainty and robustness, assumptions and data coverage, interpretation, reproduction.
- Monte Carlo uncertainty is reported, using a binomial interval such as Wilson for estimated event probabilities.
- The manifest carries schema, application, and model versions, content hashes, training cutoff, timezone, seed and RNG scheme, dependency versions, validation status, and the synthetic flag.
- Exported strings beginning with a spreadsheet control character are neutralized, and Markdown control text is escaped.
- Outputs are written atomically; an unrelated nonempty output directory is not overwritten without an explicit option.
- Forbidden claims about productivity, individuals, auto-approval safety, or exact future backlog never appear.

## Verification Notes

- A golden-file test on the rendered report for a fixed fixture.
- A test asserting reporting performs no simulation and no network access.

## Implementation Notes

Implemented the Python artifact and report layer; no other task was implemented.
Public API and limits are documented in `docs/artifacts.md`. CLI integration
remains downstream, not a success-shaped command stub.

### Workflow-v3 evidence

1. Understood the active spec, runner/metric contracts and T-014 acceptance;
   started from origin/main dc6c11ac. Taskrail validate/next selected T-014.
2. Strict TDD: initial artifact tests failed with missing artifact module, then
   passed after implementation. Truncation-label and DST elapsed-bound tests
   separately failed before their fixes. Review regressions produced 19 failed,
   20 passed before fixes, then 39 passed. Denominator follow-up cases produced
   two DID NOT RAISE failures, then two passes. A deliberate wrong model-card
   version caused the golden bundle test to fail; restoring it passed.
3. Initial full suite: 360 passed; ruff, format and mypy passed.
4. Dedicated code-simplifier loaded its skill; accepted only one backup-path
   assignment and a named report-size limit. Focused 20 tests passed afterward.
5. Independent code-reviewer lanes: General, Python and Security, each loaded
   its ECC reviewer; Python also loaded python-patterns and Security loaded
   security-review/common security rules. No SQL/database, web framework or
   additional domain lane was needed. Fresh candidate validation deduplicated
   PY-003 into G-001; no other candidate was rejected.
6. All validated findings below were fixed with failing/passing tests. No
   task-local finding was deferred.
7. Fresh disposition verification found the remaining PY-002 denominator issue;
   the second/final cycle confirmed every finding resolved and returned
   "No concrete task-relevant findings." Its complete focused suite: 43 passed.
   Final `mise run check`: 383 passed, ruff/format/mypy and all shell guards pass.
8. Taskrail verify passed and complete marked T-014 completed after these gates.
   Generated plan/report: `planning/artifacts/verify/T-014-experiment-artifacts/20260910T170417Z/`.

### Verbatim review findings and disposition

- G-001: "The generated reproduction section implies a direct artifact replay
  capability that does not exist." Fixed by stating manual Experiment
  reconstruction explicitly; golden report and dedicated regression updated.
- PY-001: "The model card cannot accurately represent derived or proxy input
  provenance and may falsely label non-synthetic templates as observed." Fixed
  with explicit template_basis and conservative assumed default; synthetic
  experiments override it, and derived/proxy/observed/assumed cases are tested.
- PY-002: "The versioned summary reader validates shape but not semantic
  invariants for replication counts, probabilities, intervals, or summary
  counts." Fixed count, finite/ordered quantile, probability and null semantics.
  Disposition follow-up: "The versioned summary reader still accepts probability
  trial counts that contradict the corresponding summary and requested
  replication counts." Fixed by tying each event/paired denominator to its
  corresponding defined count. Both malformed-artifact cases now fail validation.
- PY-003: "The generated reproduction section implies a replay capability that
  the artifact API does not provide." Duplicate of G-001, resolved by that fix.
- Security: "No concrete task-relevant findings."

### Verification and limitations

- `BASE=dc6c11ac1f24538ad757f62abe03eaa7e77801b0 mise run test:mutate`:
  artifacts 504/591 killed (85.3%), 87 survived; reporting 223/235 killed (94.9%),
  12 survived. No timeout, skipped or unchecked selected mutants. Raw counts
  were cross-checked with `uv run mutmut results --all true`; no survivors were
  removed from denominators. Initial artifact score 361/591 (61.1%) failed and
  motivated meaningful full export-contract coverage, not a lowered floor.
- Raw final mutation output: `/tmp/t014-raw-verified.txt`; full gate:
  `/tmp/t014-check-final.log`. These are orb-local, not portable evidence files.
- Manual plan/report:
  `planning/artifacts/manual-test/T-014-experiment-artifacts/20260910T165340Z/`.
  Five steps passed: nine artifacts/manifest, six-section conditional report,
  Wilson zero-event uncertainty, offline re-render, escaped exports and explicit
  overwrite protection. Ephemeral outputs were cleaned up; no web UI is added.
- Golden fixture values were inspected: baseline operational/new-ready merges
  2/1, bypass operational merge 1, paired delta -1 and relative -0.5, sampled
  replication 1 only. Complete fixtures complement independent numeric tests.
- Pydantic decorated validators are omitted from mutation discovery, not claimed
  covered by those percentages. New T-040 tracks this for the v0.1.0 release gate.
- New T-039 tracks persisted simulate/report CLI integration, executable replay
  and upstream dataset/model lineage for the v0.1.0 documented pipeline.
  Neither follow-up was implemented. Existing T-037 still owns expanded
  requested/usable/truncated presentation; no ranking is introduced here.
- 2026-09-10T17:04:17Z: verification pass
