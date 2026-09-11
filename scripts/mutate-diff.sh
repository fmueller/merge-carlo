#!/usr/bin/env bash
# Run mutation tests only for the source modules a diff touched.
#
# mutmut re-runs the test suite once per mutant, so a whole-repository run does
# not belong in a per-change loop. This selects mutants by module, which is the
# finest granularity mutmut's name filter offers, and skips the run entirely when
# a change touched no source module.
#
# Override the comparison point with BASE, for example `BASE=HEAD~3`.
set -euo pipefail

base="${BASE:-main}"

if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  echo "mutate-diff: unknown base ref: $base" >&2
  exit 2
fi

# A merge base, not the base tip: a change should be mutated against the commit
# it actually branched from, not against unrelated work landed since.
merge_base="$(git merge-base "$base" HEAD 2>/dev/null || echo "$base")"

# A plain directory pathspec, filtered to Python below: git pathspec globbing
# does not treat "*" as stopping at a slash, so a glob here would only be
# misleading about what it matches.
changed="$(git diff --name-only --diff-filter=d "$merge_base" -- src/merge_carlo/ | grep '\.py$' || true)"

if [ -z "$changed" ]; then
  echo "mutate-diff: no source modules changed since $base; nothing to mutate"
  exit 0
fi

patterns=()
scope=()
while IFS= read -r path; do
  [ -z "$path" ] && continue
  module="${path#src/}"
  module="${module%.py}"
  module="${module//\//.}"
  module="${module%.__init__}"
  patterns+=("$module.*")
  scope+=(--module "$module")
done <<<"$changed"

echo "mutate-diff: mutating ${#patterns[@]} module(s) changed since $base"
printf '  %s\n' "${patterns[@]}"

# mutmut 3.7.0 profiles only new tests against a saved stats cache, so an existing
# test that reaches a newly added function would never run against its mutants and
# they would be reported as survivors. Rebuild the test mapping on every run.
rm -f mutants/mutmut-stats.json
uv run mutmut run "${patterns[@]}"
uv run mutmut results --all true | bash "$(dirname "${BASH_SOURCE[0]}")/check-mutation-floor.sh" "${scope[@]}"
