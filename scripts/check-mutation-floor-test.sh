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

# Ten mutants, eight killed: exactly on the v0.1.0 80% floor.
at_floor=""
for i in 1 2 3 4 5 6 7 8; do
  at_floor+="    merge_carlo.engine.x__run__mutmut_$i: killed"$'\n'
done
at_floor+="    merge_carlo.engine.x__run__mutmut_9: survived"$'\n'
at_floor+="    merge_carlo.engine.x__run__mutmut_10: survived"

# Ten mutants, seven killed: below the floor.
below_floor=""
for i in 1 2 3 4 5 6 7; do
  below_floor+="    merge_carlo.engine.x__run__mutmut_$i: killed"$'\n'
done
below_floor+="    merge_carlo.engine.x__run__mutmut_8: survived"$'\n'
below_floor+="    merge_carlo.engine.x__run__mutmut_9: survived"$'\n'
below_floor+="    merge_carlo.engine.x__run__mutmut_10: survived"

# Mangled class methods use mutmut's Unicode separator. Mix them with top-level
# mutants so the fixture catches reports that silently drop either form.
mangled_methods=""
for i in 1 2 3 4; do
  mangled_methods+="    merge_carlo.runner.xǁExperimentRunǁ_iterate__mutmut_$i: killed"$'\n'
done
mangled_methods+="    merge_carlo.runner.xǁExperimentRunǁ_iterate__mutmut_5: timeout"$'\n'
mangled_methods+="    merge_carlo.runner.xǁExperimentRunǁ_iterate__mutmut_6: survived"$'\n'
mangled_methods+="    merge_carlo.runner.xǁExperimentRunǁ_iterate__mutmut_7: survived"$'\n'
for i in 8 9 10; do
  mangled_methods+="    merge_carlo.runner.x__run_replications__mutmut_$i: killed"$'\n'
done

# A weak module hidden behind a strong one; the repository total would pass.
strong="${at_floor//survived/killed}"
mixed="${strong//merge_carlo.engine/merge_carlo.metrics}"$'\n'"$below_floor"

assert_accepts at-floor "$at_floor"
assert_rejects below-floor "$below_floor" "below the mutation efficacy floor"
assert_reports raw-counts-at-floor "$at_floor" "8/10"
assert_reports raw-score-at-floor "$at_floor" "80.0%"
assert_reports rejected-floor-visible "$below_floor" "BELOW FLOOR 80%"
assert_rejects explicit-stricter-floor "$at_floor" "BELOW FLOOR 90%" --floor 90
assert_accepts below-floor-with-lower-floor "$below_floor" --floor 70
assert_accepts mangled-methods-full "$mangled_methods"
assert_reports mangled-methods-full-count "$mangled_methods" "8/10"
assert_accepts mangled-methods-scoped "$mangled_methods" --module merge_carlo.runner
assert_reports mangled-methods-scoped-count "$mangled_methods" "8/10" --module merge_carlo.runner

# Synthetic reproduction of the reported T-005 counts; no survivor is excluded.
reported_counts=""
for i in $(seq 1 39); do
  status=survived
  if [ "$i" -le 34 ]; then
    status=killed
  fi
  reported_counts+="    merge_carlo.randomness.x__stream__mutmut_$i: $status"$'\n'
done
assert_accepts reported-counts-at-v010-floor "$reported_counts"
assert_reports reported-raw-counts "$reported_counts" "34/39"
assert_reports reported-raw-score "$reported_counts" "87.2%"
assert_rejects reported-counts-at-old-floor "$reported_counts" "BELOW FLOOR 90%" --floor 90

# A timed-out mutant is a killed mutant: the mutation changed behavior enough to
# hang the suite, which the tests would have caught given time.
timeout_counts="${at_floor//survived/timeout}"
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

# Differential scope is exact, and unrelated cached outcomes never contribute.
unexecuted="${strong//killed/not checked}"
unrelated="${unexecuted//merge_carlo.engine/merge_carlo.engine_extra}"
assert_accepts selected-only "$at_floor"$'\n'"$unrelated" --module merge_carlo.engine
assert_reports selected-raw-counts "$at_floor"$'\n'"$unrelated" "8/10" --module merge_carlo.engine
assert_rejects unrelated-cannot-inflate "$mixed" "BELOW FLOOR 80%" --module merge_carlo.engine
assert_rejects missing-selected "$strong" "missing results: merge_carlo.absent" --module merge_carlo.absent
assert_rejects missing-second-selected "$strong" "missing results: merge_carlo.absent" --module merge_carlo.engine --module merge_carlo.absent
assert_rejects incomplete-selected "${at_floor/survived/not checked}" "unexecuted mutants" --module merge_carlo.engine
assert_rejects small-incomplete-selected "merge_carlo.engine.x__run__mutmut_1: not checked" "unexecuted mutants" --module merge_carlo.engine
assert_rejects full-retains-unrelated "$at_floor"$'\n'"$unrelated" "below the mutation efficacy floor"
class_unexecuted="${mangled_methods/survived/not checked}"
assert_reports mangled-methods-unexecuted-count "$class_unexecuted" "8/10"
assert_rejects mangled-methods-unexecuted-scoped "$class_unexecuted" "unexecuted mutants (1)" --module merge_carlo.runner
assert_accepts mangled-methods-selected-ignores-unrelated "$mangled_methods"$'\n'"$unrelated" --module merge_carlo.runner

# Bad arguments are refused rather than silently defaulted.
if printf '%s\n' "$at_floor" | bash "$checker" --floor ninety >/dev/null 2>&1; then
  fail "a non-numeric floor was accepted"
fi
if printf '%s\n' "$at_floor" | bash "$checker" --nonsense >/dev/null 2>&1; then
  fail "an unknown argument was accepted"
fi

bash "$script_dir/mutate-diff-test.sh"
printf 'mutation floor checks passed\n'
