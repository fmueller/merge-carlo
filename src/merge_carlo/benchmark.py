"""Reproducible performance benchmark over the SYNTHETIC offline demo workload.

Run with ``uv run python -m merge_carlo.benchmark --out DIR``. The record states
what was measured on one machine; it is not a runtime or scalability promise.
"""

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, replace
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from merge_carlo import __version__
from merge_carlo.artifacts import DEPENDENCY_NAMES, Evidence, write_experiment
from merge_carlo.demo import demo_experiment
from merge_carlo.simulation.runner import Experiment, run_experiment


@dataclass(frozen=True, slots=True)
class Hardware:
    system: str
    release: str
    machine: str
    processor: str | None
    cpu_count: int | None


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    """Parameters, environment and measurements of one sequential benchmark run.

    Peak RSS is the whole process high-water mark, including interpreter and
    imports; ``startup_peak_rss_bytes`` is that mark before the timed run.
    """

    schema_version: int
    workload: str
    application_version: str
    seed: int
    replications: int
    traced_replications: int
    assumption_sets: int
    scenarios: int
    simulated_runs: int
    engine_events: int
    wall_seconds: float
    startup_peak_rss_bytes: int | None
    peak_rss_bytes: int | None
    output_bytes: int
    trace_bytes: int
    python_version: str
    dependency_versions: dict[str, str]
    hardware: Hardware


def peak_rss_bytes() -> int | None:
    """Process peak resident set size; None where the platform has no rusage."""
    if sys.platform == "win32":
        return None
    import resource

    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kibibytes; macOS reports bytes.
    return maximum if sys.platform == "darwin" else maximum * 1024


_CPUINFO = Path("/proc/cpuinfo")


def _processor() -> str | None:
    if _CPUINFO.is_file():
        for line in _CPUINFO.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def _engine_events(experiment: Experiment) -> int:
    """Distinct event times the engine processed, counting a shared baseline once."""
    traced = replace(experiment, trace_replications=tuple(range(experiment.replications)))
    events = 0
    previous_baseline: tuple[str, int] | None = None
    for row in run_experiment(traced):
        assert row.trace is not None
        baseline, scenario = row.trace
        if (row.assumption_id, row.replication) != previous_baseline:
            events += len(baseline.boundaries)
            previous_baseline = (row.assumption_id, row.replication)
        if row.scenario_id != "baseline":
            events += len(scenario.boundaries)
    return events


def run_benchmark(out: Path, *, seed: int, replications: int, traced_replications: int) -> BenchmarkRecord:
    """Time one artifact bundle, then count engine events in an untimed replay."""
    demo = demo_experiment(seed, replications)
    if type(traced_replications) is not int or not 0 <= traced_replications <= replications:
        raise ValueError("traced replications must be between zero and the replication count")
    experiment = replace(demo, trace_replications=tuple(range(traced_replications)))
    startup_rss = peak_rss_bytes()
    started = perf_counter()
    write_experiment(experiment, Evidence(synthetic=True, training_cutoff=None), out)
    wall_seconds = perf_counter() - started
    peak_rss = peak_rss_bytes()
    return BenchmarkRecord(
        schema_version=1,
        workload="synthetic-demo",
        application_version=__version__,
        seed=seed,
        replications=replications,
        traced_replications=traced_replications,
        assumption_sets=len(experiment.assumptions),
        scenarios=len(experiment.scenarios),
        simulated_runs=len(experiment.assumptions) * replications * (len(experiment.scenarios) + 1),
        engine_events=_engine_events(experiment),
        wall_seconds=wall_seconds,
        startup_peak_rss_bytes=startup_rss,
        peak_rss_bytes=peak_rss,
        output_bytes=sum(path.stat().st_size for path in out.iterdir()),
        trace_bytes=(out / "traces.jsonl").stat().st_size,
        python_version=platform.python_version(),
        dependency_versions={name: version(name) for name in DEPENDENCY_NAMES},
        hardware=Hardware(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            processor=_processor(),
            cpu_count=os.cpu_count(),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m merge_carlo.benchmark",
        description="Benchmark the SYNTHETIC demo workload sequentially and print a JSON record.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Empty or absent directory for the artifact bundle.")
    parser.add_argument("--seed", type=int, default=42, help="Root random seed.")
    parser.add_argument("--replications", type=int, default=200, help="Paired replications per scenario.")
    parser.add_argument("--traced-replications", type=int, default=2, help="Leading replications with traces.")
    arguments = parser.parse_args(argv)
    try:
        record = run_benchmark(
            arguments.out,
            seed=arguments.seed,
            replications=arguments.replications,
            traced_replications=arguments.traced_replications,
        )
    except (ValueError, OSError) as exc:
        print(f"Cannot run benchmark: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(record), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
