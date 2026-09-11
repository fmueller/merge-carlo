# Performance benchmark

This page records what one sequential benchmark run measured on one machine. It
is evidence about that run, not a performance contract. No universal runtime,
throughput, memory, or scalability promise follows from it: wall time depends on
hardware, load, Python and library versions, and above all on the workload
(arrival volume, duty windows, revision loops, horizon, and scenario count).

## Command

```bash
uv sync --locked
uv run python -m merge_carlo.benchmark --out <empty-or-absent-dir> \
  --seed 42 --replications 200 --traced-replications 2
```

The defaults are `--seed 42 --replications 200 --traced-replications 2`. The
command writes the complete SYNTHETIC demo artifact bundle to `--out` and prints
one JSON record to standard output. Invalid parameters or a nonempty output
directory exit `2` with a `Cannot run benchmark:` message.

## Workload

The workload is the offline demo experiment (`merge_carlo.demo.demo_experiment`),
whose inputs are synthetic and never measured team behavior: two synthetic
template weeks of 15 and 20 ready pull requests, one reviewer on a two-hour
weekday duty window, a seven-day warm-up and seven-day measurement horizon, one
assumption set (1,800 s constant active service with revision loops), and five
scenarios plus the implicit baseline. Traces are kept only for the leading
`--traced-replications` replication indexes.

## Record fields

| Field | Meaning |
| --- | --- |
| `"workload"`, `"seed"`, `"replications"`, `"traced_replications"` | Parameters needed to rerun the same workload |
| `"assumption_sets"`, `"scenarios"`, `"simulated_runs"` | Counts; runs are assumption sets × replications × (scenarios + baseline) |
| `"engine_events"` | Distinct event times processed by the engine across all runs, counting each shared baseline once; counted in an untimed replay after the timed run |
| `"wall_seconds"` | `perf_counter` time for building and publishing the artifact bundle only |
| `"startup_peak_rss_bytes"`, `"peak_rss_bytes"` | Process peak resident set size before and after the timed run, including interpreter and imports; `null` where the platform has no `resource` module |
| `"output_bytes"`, `"trace_bytes"` | Total bundle size and the size of `traces.jsonl` |
| `"python_version"`, `"dependency_versions"`, `"application_version"` | Software environment |
| `"hardware"` | Operating system, release, machine, processor model, and logical CPU count |

## Recorded results

Recorded on 2026-09-11 from the locked environment on an otherwise idle
workstation. Each row is a fresh process, run sequentially.

Environment: Linux 7.0.0-31-generic, x86_64, AMD Ryzen 9 5950X 16-Core Processor
(32 logical CPUs); Python 3.13.11; httpx 0.28.1, numpy 2.5.3, pydantic 2.13.5,
pyyaml 6.0.3, simpy 4.1.2, typer 0.27.2; merge-carlo 0.1.0.

| Replications | Traced | Simulated runs | Engine events | Wall seconds | Startup peak RSS | Peak RSS | Output bytes | Trace bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 2 | 300 | 36,084 | 3.83 | 48,074,752 | 53,915,648 | 1,726,832 | 707,785 |
| 200 | 2 | 1,200 | 145,155 | 14.41 | 48,926,720 | 58,507,264 | 4,299,693 | 707,785 |
| 200 (repeat) | 2 | 1,200 | 145,155 | 15.01 | — | 58,200,064 | 4,299,693 | 707,785 |
| 800 | 2 | 4,800 | 574,525 | 57.46 | 48,992,256 | 71,426,048 | 14,585,391 | 707,785 |

The full record for the default 200-replication run:

```json
{
  "application_version": "0.1.0",
  "assumption_sets": 1,
  "dependency_versions": {
    "httpx": "0.28.1",
    "numpy": "2.5.3",
    "pydantic": "2.13.5",
    "pyyaml": "6.0.3",
    "simpy": "4.1.2",
    "typer": "0.27.2"
  },
  "engine_events": 145155,
  "hardware": {
    "cpu_count": 32,
    "machine": "x86_64",
    "processor": "AMD Ryzen 9 5950X 16-Core Processor",
    "release": "7.0.0-31-generic",
    "system": "Linux"
  },
  "output_bytes": 4299693,
  "peak_rss_bytes": 58507264,
  "python_version": "3.13.11",
  "replications": 200,
  "scenarios": 5,
  "schema_version": 1,
  "seed": 42,
  "simulated_runs": 1200,
  "startup_peak_rss_bytes": 48926720,
  "trace_bytes": 707785,
  "traced_replications": 2,
  "wall_seconds": 14.410187248000057,
  "workload": "synthetic-demo"
}
```

Semantic counts and output sizes repeat exactly under the same seed; wall time
and RSS vary between runs (14.41 s and 15.01 s for the same 200-replication
workload).

## Memory

Replication rows stream: the runner holds one baseline/scenario pair at a time
and the artifact writer serializes each row to JSON Lines immediately, without
retaining simulated pull-request states. Traces are sampled: `trace_bytes` is the
same 707,785 bytes at 50, 200, and 800 replications because only the two traced
replication indexes are written. `tests/unit/benchmark_test.py` asserts that
trace rows are limited to the configured indexes, and
`tests/unit/simulation/runner_test.py` asserts that stream memory is bounded by a
pair rather than by the replication count.

Memory is not constant in the replication count. Exact medians, intervals, and
event probabilities in `summary.json` need every per-replication metric scalar,
so the writer retains those scalars until the summary is computed. Peak RSS above
startup grew from 5.8 MB at 50 replications to 22.4 MB at 800, roughly 21 KB per
additional replication for this six-run-per-replication workload.

## Profile

A `cProfile` run of `write_experiment` on the same workload at 50 replications
(10.3 s under the profiler, 3.83 s without it) showed:

| Share of profiled time | Where |
| --- | --- |
| 8.1 s cumulative | `run_fifo` over 300 simulated runs, single-threaded |
| 1.9 s | exact `Fraction` comparisons inside the engine event loop |
| 2.0 s | constructing a new pydantic `TypeAdapter` for each serialized row (1,001 constructions) |
| 0.9 s | purpose-keyed random stream construction (29,978 streams) |

Parallel workers are not added in v0.1.0. The profile does not show a bottleneck
that workers are the first remedy for: the default demo completes in about
15 seconds on the recorded machine, the dominant costs are serial per-run and
per-row overheads, and workers would require an ordered merge of streamed rows to
keep artifacts byte-identical under a fixed seed. Reuse of serialization
adapters and engine arithmetic are the measured candidates to examine first if a
real workload needs it; this is a profile observation, not a planned change.
