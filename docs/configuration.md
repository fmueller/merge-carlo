# Configuration contracts

`merge-carlo schema --out out/schemas` writes versioned Draft 2020-12 JSON
Schemas for assumption and scenario YAML. The destination must be empty or
absent; publication is staged so a failure does not leave a partial schema set.
Repeated exports from the same application version are byte-identical.

The matching data-only examples are [`examples/assumptions.yaml`](../examples/assumptions.yaml)
and [`examples/scenarios.yaml`](../examples/scenarios.yaml). Configuration is
limited to one megabyte, loaded with PyYAML's safe loader, and validated by
strict Pydantic models. Unknown keys, Python object tags, invalid schema
versions, non-finite numbers, and values outside their declared domains are
rejected. Configuration values are never evaluated and cannot name a Python
class or shell command to invoke.

## Durations and effort sensitivity

Active review service uses only positive constant, lognormal, or empirical
duration distributions. Lognormal `median_seconds` is the median and `sigma` is
the log-space standard deviation; it is not a mean-and-sigma parameterization.

Each named assumption set may apply a finite positive `effort_multiplier`.
Composition is explicit:

```text
effective active-service seconds =
    max(1, ceil(sampled active-service seconds × effort_multiplier))
```

This multiplier is an assumed sensitivity parameter, not an observed
productivity effect. Zero is not valid active review service. Zero delays are
permitted only for coordination phases such as verification, author response,
and post-approval merge coordination.

## Scenario semantics

The baseline is implicit and cannot be named as a scenario. Additive AI demand
adds an assumed fraction of a sampled baseline week; replacement AI demand
reassigns an assumed fraction of known-human arrivals without changing unknown
or non-AI automation origins. Scenarios may also replace named duty calendars,
declare reviewer absences, or configure hypothetical review bypass. These are
inputs to the model, not measured team behavior or policy recommendations.
Additive demand fractions are finite and bounded at `1000`; the runner also
accounts for their amplified proposal counts in its estimated-work limit before
constructing a schedule.

## Persisted execution

The scenario document may include an `execution` section for the persisted
`simulate` command:

```yaml
execution:
  observation_start: "2026-09-07T00:00:00"
  horizon_days: 7
  warmup_days: 7
  root_seed: 42
  replications: 200
  calendars:
    - name: review-duty
      timezone: Europe/Berlin
      windows:
        - name: weekday-morning
          weekday: 0
          start: "09:00:00"
          end: "17:00:00"
  reviewers:
    - name: reviewer
      calendar: review-duty
```

`observation_start` is a naive local time in the calibrated model timezone;
the command rejects offset-bearing values rather than guessing. The runner
records the resulting UTC bounds and elapsed seconds. `root_seed`, replication
counts, sampled trace indexes, fixed-horizon seconds, and backlog threshold are
also versioned inputs. A scenario calendar replaces the named base calendar;
an absence names one of the declared reviewers. Missing execution metadata uses
conservative defaults for compatibility, but production runs should declare
capacity explicitly.
