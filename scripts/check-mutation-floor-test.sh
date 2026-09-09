#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
checker="$script_dir/check-mutation-floor.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_accepts() {
  local name="$1"
  local results="$2"
  shift 2
  local output
  if ! output="$(printf '%s\n' "$results" | bash "$checker" "$@" 2>&1)"; then
    fail "$name was rejected: $output"
  fi
}

assert_rejects() {
  local name="$1"
  local results="$2"
  local expected="$3"
  shift 3
  local output
  if output="$(printf '%s\n' "$results" | bash "$checker" "$@" 2>&1)"; then
    fail "$name was accepted"
  fi
  if [[ "$output" != *"$expected"* ]]; then
    fail "$name did not report '$expected': $output"
  fi
}

assert_reports() {
  local name="$1"
  local results="$2"
  local expected="$3"
  shift 3
  local output
  output="$(printf '%s\n' "$results" | bash "$checker" "$@" 2>&1)" || true
  if [[ "$output" != *"$expected"* ]]; then
    fail "$name did not report '$expected': $output"
  fi
}

# Ten mutants, nine killed: exactly on a 90% floor.
at_floor=""
for i in 1 2 3 4 5 6 7 8 9; do
  at_floor+="    merge_carlo.engine.x__run__mutmut_$i: killed"$'\n'
done
at_floor+="    merge_carlo.engine.x__run__mutmut_10: survived"

# Ten mutants, eight killed: below a 90% floor.
below_floor=""
for i in 1 2 3 4 5 6 7 8; do
  below_floor+="    merge_carlo.engine.x__run__mutmut_$i: killed"$'\n'
done
below_floor+="    merge_carlo.engine.x__run__mutmut_9: survived"$'\n'
below_floor+="    merge_carlo.engine.x__run__mutmut_10: survived"

# A weak module hidden behind a strong one; the repository total would pass.
mixed="$at_floor"$'\n'"$below_floor"
mixed="${mixed//merge_carlo.engine.x__run__mutmut_9: survived/merge_carlo.metrics.x__p95__mutmut_9: survived}"

assert_accepts at-floor "$at_floor"
assert_rejects below-floor "$below_floor" "below the mutation efficacy floor"
assert_accepts below-floor-with-lower-floor "$below_floor" --floor 80

# A timed-out mutant is a killed mutant: the mutation changed behavior enough to
# hang the suite, which the tests would have caught given time.
timeout_counts="${at_floor//merge_carlo.engine.x__run__mutmut_10: survived/merge_carlo.engine.x__run__mutmut_10: timeout}"
assert_accepts timeout-counts-as-killed "$timeout_counts" --floor 100

# Too few mutants is not a verdict in either direction.
assert_accepts insufficient-evidence "    merge_carlo.cli.x__version__mutmut_1: survived"
assert_reports insufficient-evidence-is-labeled "    merge_carlo.cli.x__version__mutmut_1: survived" "insufficient evidence"
assert_rejects at-min-mutants-is-evaluated "$below_floor" "below the mutation efficacy floor" --min-mutants 10

# The floor is per module, so a weak module is not hidden by a strong one.
assert_rejects per-module-not-repository-total "$mixed" "below the mutation efficacy floor"

# Output ordering is stable regardless of awk hash ordering.
first="$(printf '%s\n' "$mixed" | bash "$checker" 2>/dev/null || true)"
second="$(printf '%s\n' "$mixed" | bash "$checker" 2>/dev/null || true)"
if [[ "$first" != "$second" ]]; then
  fail "output was not stable across runs"
fi

assert_rejects no-results "" "no mutation results were found"

# Bad arguments are refused rather than silently defaulted.
if printf '%s\n' "$at_floor" | bash "$checker" --floor ninety >/dev/null 2>&1; then
  fail "a non-numeric floor was accepted"
fi
if printf '%s\n' "$at_floor" | bash "$checker" --nonsense >/dev/null 2>&1; then
  fail "an unknown argument was accepted"
fi

printf 'mutation floor checks passed\n'
