#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/bin"
export MUTATION_FIXTURE="$tmp/results" MUTATION_CALLS="$tmp/calls"
cat >"$tmp/bin/git" <<'SH'
#!/usr/bin/env bash
case "$1" in
  rev-parse|merge-base) echo main ;;
  diff) printf '%s\n' src/merge_carlo/engine.py ;;
  *) exit 2 ;;
esac
SH
cat >"$tmp/bin/uv" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$MUTATION_CALLS"
case "$*" in
  'run mutmut run merge_carlo.engine.*') exit "${RUN_STATUS:-0}" ;;
  'run mutmut results --all true') cat "$MUTATION_FIXTURE"; exit "${RESULT_STATUS:-0}" ;;
  *) exit 2 ;;
esac
SH
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH"

for i in $(seq 1 10); do
  printf 'merge_carlo.engine.x__run__mutmut_%s: killed\n' "$i"
  printf 'merge_carlo.calendars.x__run__mutmut_%s: not checked\n' "$i"
done >"$MUTATION_FIXTURE"
if ! output="$(bash "$script_dir/mutate-diff.sh" 2>&1)"; then
  echo "FAIL: engine-only differential run: $output" >&2
  exit 1
fi
[[ "$output" == *'10/10'* ]] || { echo 'FAIL: selected raw counts missing'; exit 1; }
[[ "$output" != *'merge_carlo.calendars'* ]] || { echo 'FAIL: unrelated verdict'; exit 1; }
grep -Fx 'run mutmut results --all true' "$MUTATION_CALLS" >/dev/null

# Both tool failures must survive the reporting pipeline.
for variable in RUN_STATUS RESULT_STATUS; do
  if env "$variable=7" bash "$script_dir/mutate-diff.sh" >"$tmp/output" 2>&1; then
    echo "FAIL: $variable failure was hidden" >&2
    exit 1
  fi
done
printf 'merge_carlo.calendars.x__run__mutmut_1: killed\n' >"$MUTATION_FIXTURE"
if bash "$script_dir/mutate-diff.sh" >"$tmp/output" 2>&1; then
  echo 'FAIL: missing selected results passed' >&2
  exit 1
fi
grep -F 'missing results: merge_carlo.engine' "$tmp/output" >/dev/null
printf 'differential mutation checks passed\n'
