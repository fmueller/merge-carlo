"""Performance benchmark records its workload, environment and measurements."""

import json
import os
import platform
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from merge_carlo import __version__
from merge_carlo.benchmark import _processor, main, peak_rss_bytes, run_benchmark

pytestmark = pytest.mark.unit


def test_record_carries_parameters_environment_and_measurements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock: Iterator[float] = iter((10.0, 12.5))
    monkeypatch.setattr("merge_carlo.benchmark.perf_counter", lambda: next(clock))
    out = tmp_path / "bundle"

    record = run_benchmark(out, seed=7, replications=2, traced_replications=1)

    assert record.schema_version == 1
    assert record.workload == "synthetic-demo"
    assert record.application_version == __version__
    assert (record.seed, record.replications, record.traced_replications) == (7, 2, 1)
    assert (record.assumption_sets, record.scenarios) == (1, 5)
    assert record.simulated_runs == 1 * 2 * (5 + 1)
    assert record.wall_seconds == 2.5
    assert record.output_bytes == sum(path.stat().st_size for path in out.iterdir())
    assert record.trace_bytes == (out / "traces.jsonl").stat().st_size > 0
    assert set(record.dependency_versions) == {"numpy", "simpy", "pydantic", "httpx", "pyyaml", "typer"}
    assert record.python_version == platform.python_version()
    assert record.hardware.machine == platform.machine()
    assert record.hardware.system == platform.system()
    assert record.hardware.release == platform.release()
    assert record.hardware.cpu_count == os.cpu_count()
    if Path("/proc/cpuinfo").is_file():
        assert record.hardware.processor
    assert json.loads((out / "manifest.json").read_text())["synthetic"] is True
    if sys.platform != "win32":
        assert record.startup_peak_rss_bytes is not None
        assert record.peak_rss_bytes is not None
        assert record.peak_rss_bytes >= record.startup_peak_rss_bytes > 0


def test_trace_retention_respects_configured_sampling_bound(tmp_path: Path) -> None:
    sampled = run_benchmark(tmp_path / "sampled", seed=3, replications=3, traced_replications=2)
    traces = [json.loads(line) for line in (tmp_path / "sampled" / "traces.jsonl").read_text().splitlines()]
    assert len(traces) == 2 * sampled.scenarios
    assert {row["replication"] for row in traces} == {0, 1}

    unsampled = run_benchmark(tmp_path / "unsampled", seed=3, replications=3, traced_replications=0)
    assert (tmp_path / "unsampled" / "traces.jsonl").read_bytes() == b""
    assert unsampled.trace_bytes == 0
    assert unsampled.engine_events == sampled.engine_events


def test_engine_events_count_processed_event_times_once_per_simulated_run(tmp_path: Path) -> None:
    record = run_benchmark(tmp_path / "all", seed=5, replications=2, traced_replications=2)
    expected = 0
    seen: set[tuple[str, int]] = set()
    for line in (tmp_path / "all" / "traces.jsonl").read_text().splitlines():
        row = json.loads(line)
        baseline, scenario = row["diagnostics"]
        if (row["assumption"], row["replication"]) not in seen:
            seen.add((row["assumption"], row["replication"]))
            expected += len(baseline["boundaries"])
        expected += len(scenario["boundaries"])
    assert len(seen) == 2
    assert record.engine_events == expected > 0


@pytest.mark.parametrize("traced", [-1, 3])
def test_traced_replications_must_select_existing_replications(tmp_path: Path, traced: int) -> None:
    with pytest.raises(ValueError, match="^traced replications"):
        run_benchmark(tmp_path / "out", seed=1, replications=2, traced_replications=traced)
    assert not (tmp_path / "out").exists()


def test_invalid_replications_are_reported_before_the_trace_bound(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="^replications must be a positive integer"):
        run_benchmark(tmp_path / "out", seed=1, replications=-1, traced_replications=0)
    assert not (tmp_path / "out").exists()


def test_processor_reads_cpu_model_name_then_falls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_bytes(b"processor\t: 0\nmodel name\t: Vendor CPU: v2 \xff\nflags\t: fpu\n")
    monkeypatch.setattr("merge_carlo.benchmark._CPUINFO", cpuinfo)
    assert _processor() == "Vendor CPU: v2 \ufffd"

    monkeypatch.setattr("merge_carlo.benchmark._CPUINFO", tmp_path / "absent")
    monkeypatch.setattr("platform.processor", lambda: "arm")
    assert _processor() == "arm"
    monkeypatch.setattr("platform.processor", lambda: "")
    assert _processor() is None


@pytest.mark.parametrize(("system", "expected"), [("linux", 5 * 1024), ("darwin", 5), ("win32", None)])
def test_peak_rss_normalizes_platform_units(monkeypatch: pytest.MonkeyPatch, system: str, expected: int | None) -> None:
    monkeypatch.setattr("merge_carlo.benchmark.sys.platform", system)
    monkeypatch.setattr("resource.getrusage", lambda who: SimpleNamespace(ru_maxrss=5))
    assert peak_rss_bytes() == expected


def test_main_prints_json_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "bundle"
    assert main(["--out", str(out), "--seed", "3", "--replications", "1", "--traced-replications", "1"]) == 0
    output = capsys.readouterr().out
    record = json.loads(output)
    assert output == json.dumps(record, indent=2, sort_keys=True) + "\n"
    assert (record["seed"], record["replications"], record["traced_replications"]) == (3, 1, 1)
    assert record["workload"] == "synthetic-demo"
    assert record["hardware"]["cpu_count"] == os.cpu_count()
    assert (out / "report.md").is_file()


def test_main_defaults_record_the_documented_workload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, int, int, int]] = []

    def fake(out: Path, *, seed: int, replications: int, traced_replications: int) -> object:
        calls.append((out, seed, replications, traced_replications))
        raise ValueError("stop")

    monkeypatch.setattr("merge_carlo.benchmark.run_benchmark", fake)
    assert main(["--out", str(tmp_path)]) == 2
    assert calls == [(tmp_path, 42, 200, 2)]
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


def test_main_rejects_invalid_input_without_traceback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--out", str(tmp_path / "a"), "--replications", "1", "--traced-replications", "2"]) == 2
    error = capsys.readouterr().err
    assert error.startswith("Cannot run benchmark:")
    assert "Traceback" not in error

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep", encoding="utf-8")
    assert main(["--out", str(occupied), "--replications", "1", "--traced-replications", "0"]) == 2
    assert capsys.readouterr().err.startswith("Cannot run benchmark:")
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "keep"
