#!/usr/bin/env bash
# Enforce a per-module mutation efficacy floor from a completed mutmut run.
#
# mutmut reports one repository-wide total, which hides a weakly tested module
# behind a well tested one. This reads the per-mutant statuses the run already
# recorded and applies the floor to each module separately; it never runs mutmut
# a second time.
#
# A module with too few mutants gets no verdict. A percentage over three mutants
# describes the sample, not the tests, and failing on it would only teach people
# to write mutation-shaped code. Such a module is reported as insufficient
# evidence, which is the same answer this project gives anywhere else the
# evidence does not support a conclusion.
#
# Reads `mutmut results --all true` on stdin, or runs it when given no input.
set -euo pipefail

floor=80
min_mutants=10

while [ "$#" -gt 0 ]; do
  case "$1" in
    --floor)
      floor="${2:-}"
      shift 2
      ;;
    --min-mutants)
      min_mutants="${2:-}"
      shift 2
      ;;
    *)
      echo "check-mutation-floor: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$floor" in
  ''|*[!0-9]*)
    echo "check-mutation-floor: --floor must be a whole number of percent" >&2
    exit 2
    ;;
esac
case "$min_mutants" in
  ''|*[!0-9]*)
    echo "check-mutation-floor: --min-mutants must be a whole number" >&2
    exit 2
    ;;
esac

if [ -t 0 ]; then
  results="$(mutmut results --all true)"
else
  results="$(cat)"
fi

# A result line is "    <module>.<function>__mutmut_<n>: <status>". The module is
# everything before the mangled function name, so a status is attributed to the
# file it came from rather than to the repository as a whole.
printf '%s\n' "$results" | awk -v floor="$floor" -v min_mutants="$min_mutants" '
  match($0, /^[[:space:]]*[A-Za-z_][A-Za-z0-9_.]*__mutmut_[0-9]+:[[:space:]]*[a-z_ ]+$/) {
    split($0, parts, ":")
    name = parts[1]
    status = parts[2]
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)

    # Strip the mangled function segment: "pkg.mod.x__fn__mutmut_3" -> "pkg.mod".
    sub(/\.[^.]*__mutmut_[0-9]+$/, "", name)
    module = name

    total[module]++
    if (status == "killed" || status == "timeout") {
      killed[module]++
    }
    next
  }
  END {
    if (length(total) == 0) {
      print "check-mutation-floor: no mutation results were found" > "/dev/stderr"
      exit 2
    }

    n = 0
    for (module in total) {
      modules[++n] = module
    }
    # Stable output regardless of awk hash ordering.
    for (i = 1; i < n; i++) {
      for (j = i + 1; j <= n; j++) {
        if (modules[j] < modules[i]) {
          swap = modules[i]; modules[i] = modules[j]; modules[j] = swap
        }
      }
    }

    failed = 0
    for (i = 1; i <= n; i++) {
      module = modules[i]
      k = killed[module] + 0
      t = total[module]
      efficacy = 100 * k / t
      if (t < min_mutants) {
        printf "  %-40s %3d/%-3d  %5.1f%%  insufficient evidence (%d mutants, floor needs %d)\n", module, k, t, efficacy, t, min_mutants
      } else if (efficacy + 0.0000001 < floor) {
        printf "  %-40s %3d/%-3d  %5.1f%%  BELOW FLOOR %d%%\n", module, k, t, efficacy, floor
        failed = 1
      } else {
        printf "  %-40s %3d/%-3d  %5.1f%%  ok\n", module, k, t, efficacy
      }
    }

    if (failed) {
      print "check-mutation-floor: a module is below the mutation efficacy floor" > "/dev/stderr"
      exit 1
    }
    exit 0
  }
'
