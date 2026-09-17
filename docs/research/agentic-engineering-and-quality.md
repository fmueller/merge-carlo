# Agentic engineering and AI coding quality

## Main conclusion

Recent evidence does not justify the statement “AI code has a fixed higher bug
rate.” It does justify modeling agentic work as a distinct, context-dependent
workflow with its own task mix, change shape, verification behavior, human
intervention, review demand, and post-merge quality signals.

Merge rate is especially unsafe as a quality proxy. A change can be merged
because it is small, well-scoped, or easy to review while still carrying a
quality issue. Conversely, an unmerged change can be abandoned, duplicated, or
misaligned without containing a defect.

## Evidence from real pull requests

### Post-merge quality is not the same as merge success

[Cynthia, Muttakin, and Roy (MSR 2026)](https://doi.org/10.1145/3793302.3793615)
analyzed 1,210 merged agent-generated bug-fix PRs from 206 Python repositories.
They compared static-analysis results before and after merge using SonarQube.
Raw issue differences between agents largely disappeared after normalizing for
code churn. Code smells dominated; functional bugs were less frequent but could
be severe. The study's key limitation is that these are static-analysis signals
from merged Python bug-fix PRs, not a matched estimate of escaped production
defects.

[Fu et al. (TOSEM 2025)](https://doi.org/10.1145/3716848) studied security
weaknesses in Copilot-generated code found in GitHub projects. It demonstrates
that security-specific analysis is important, but security findings from static
or manual analysis should remain a separate outcome family from ordinary
functional defect rates.

### Merge outcomes contain socio-technical signals

[Ehsani et al. (MSR 2026)](https://doi.org/10.1145/3793302.3793579)
characterized 33,596 PRs from five coding agents. Across their dataset, 71.48%
were merged. Not-merged PRs tended to be larger, touch more files, and have more
CI failures. In a manual sample of rejected PRs, reviewer abandonment,
duplicates, CI/test failures, unwanted features, and agent misalignment were
important rejection patterns.

This supports a conditional merge or closure hazard using task type, size,
files, CI, review engagement, revisions, abandonment, capacity, and queue
conditions. It does not support assigning a stable merge probability to a
person or treating agent identity as intrinsic quality.

[Watanabe et al. (2025)](https://arxiv.org/abs/2509.14745) traced 567 Claude
Code PRs across 157 open-source projects. Their analysis reports lower
acceptance for agent-authored PRs than human-authored PRs in that sample and
examines revision effort and rejection reasons. It is observational and tied to
one agent and a selected set of repositories, so it is evidence for process
heterogeneity, not a general population rate.

[Ogenrwot and Businge (MSR 2026)](https://doi.org/10.1145/3793302.3793603) compared
24,014 merged agentic PRs with 5,081 merged human PRs. Agentic PRs differed in
commit structure, files touched, and deleted lines, while additions and total
line changes were more similar. Because the sample contains merged PRs only,
it cannot estimate rejection or escaped-defect risk without selection bias.

[Behind Agentic Pull Requests (MSR 2026)](https://doi.org/10.1145/3793302.3793586)
found that human intervention can be less frequent but more costly when it does
occur on agent-authored PRs. Review and coordination effort therefore belongs in
the workflow model, not only in a code-quality label.

## Evidence from agent repair and benchmarks

[Rondon et al. (ICSE-SEIP 2025)](https://doi.org/10.1109/ICSE-SEIP66354.2025.00038)
evaluated an agent on 178 Google bugs. With 20 trajectories, patches passed
bug tests for 73% of machine-reported and 25.6% of human-reported bugs, while
manual examination found semantically valid patches for only 43% and 17.9%
respectively. Test passage is therefore a useful verification signal, not a
production-quality or defect-escape label.

[Ceka et al. (2025)](https://arxiv.org/abs/2506.08311) studied repair-agent
traceability and reported that reproducing issues, generating tests, and
selecting relevant regression tests remain bottlenecks. This supports recording
agent test/tool behavior and human verification rather than only recording the
final diff.

[SWE-EVO (2025)](https://arxiv.org/abs/2512.18470) extends repository-level
evaluation toward long-horizon, multi-file software evolution. Its motivation
is important for merge-carlo: isolated issue resolution does not capture
regression risk, maintenance, or queue consequences over successive changes.
Its current dataset is small and Python-only, so it is a benchmark direction,
not a defect-rate estimate.

[Human-Written vs. AI-Generated Code (2025)](https://arxiv.org/abs/2508.21634)
compares large numbers of generated samples using defect, vulnerability, and
complexity classifications. It reports different defect profiles rather than
a single universal quality ordering. Its controlled/generated-sample setting
should not be treated as evidence about merged repository PRs.

## Process and context

[Agent READMEs (2025)](https://arxiv.org/abs/2511.12884) analyzed 2,303 agent
context files from 1,925 repositories across Claude Code, Codex, and Copilot.
The study reinforces that repository instructions and context are part of the
agentic process. They should not be conflated with author origin or used as a
developer score.

The [Google RCT](https://arxiv.org/abs/2410.12944) found a 21% time reduction
for one enterprise task with AI features, while the [METR RCT](https://arxiv.org/abs/2507.09089)
found early-2025 tools made experienced open-source developers 19% slower on
their selected tasks. These results concern productivity and task time, not
defect rates, but they demonstrate why Merge Carlo should not translate faster
coding into assumed higher throughput or quality.

## Modeling implications

Agentic work should carry separate, optional observations for:

- assisted versus agent-authored work;
- tool or agent family and version;
- autonomy level and human intervention;
- agent iterations and test/tool use;
- task type, size, files, churn, and CI outcomes;
- reviewer engagement, revisions, and abandonment;
- repository context or instructions; and
- post-merge quality evidence with an explicit linkage basis.

These observations should support pooled or hierarchical analysis with temporal
holdouts and matched human baselines where available. They should not become an
agent leaderboard, contributor ranking, or universal AI defect multiplier.
