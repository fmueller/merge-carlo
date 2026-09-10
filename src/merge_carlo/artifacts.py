"""Stream experiment artifacts into a staged, versioned local directory."""

import csv
import hashlib
import json
import platform
import shutil
import tempfile
from collections import defaultdict
from dataclasses import fields
from importlib.metadata import version
from pathlib import Path
from typing import TextIO

from pydantic import TypeAdapter

from merge_carlo import __version__
from merge_carlo.reporting import Comparison, Summary, SummaryRow, render_report, wilson
from merge_carlo.reporting import Evidence as Evidence
from merge_carlo.simulation.arrivals import AdditiveAI
from merge_carlo.simulation.metrics import HorizonShare, Metric, MetricDictionary, summarize_metrics
from merge_carlo.simulation.runner import Experiment, run_experiment


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n"


def _write(path: Path, value: object) -> None:
    path.write_text(_json(value), encoding="utf-8")


def _line(stream: TextIO, value: object) -> None:
    stream.write(_json(value))


def spreadsheet(value: str) -> str:
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value


def _metrics(dictionary: MetricDictionary | None) -> dict[str, Metric]:
    values: dict[str, Metric] = {}
    for field in fields(MetricDictionary):
        value = getattr(dictionary, field.name) if dictionary is not None else None
        if isinstance(value, HorizonShare):
            values[field.name] = value.share
            for count in ("total", "eligible", "excluded"):
                values[f"{field.name}.{count}"] = Metric(getattr(value, count))
        elif isinstance(value, Metric):
            values[field.name] = value
        else:
            values[field.name] = Metric(value, "engine_truncated" if dictionary is None else None)
            if dictionary is None and field.name in ("reviewed", "merged"):
                for count in ("total", "eligible", "excluded"):
                    values[f"{field.name}.{count}"] = Metric(None, "engine_truncated")
    return values


def _bundle(experiment: Experiment, evidence: Evidence, stage: Path) -> None:
    resolved = TypeAdapter(Experiment).dump_python(experiment, mode="json")
    configuration = {
        "schema_version": 1,
        "synthetic": evidence.synthetic,
        "experiment": resolved,
        "elapsed_seconds": {
            "warmup": experiment.bounds.warmup_seconds,
            "measurement": experiment.bounds.observation.seconds,
        },
        # Both intervention dataclasses have a fraction; preserve their distinct semantics.
        "demand_kinds": {
            scenario.name: "additive" if isinstance(scenario.demand, AdditiveAI) else "replacement"
            for scenario in experiment.scenarios
            if scenario.demand is not None
        },
    }
    _write(stage / "resolved-scenarios.json", configuration)
    _write(
        stage / "model-card.json",
        {
            "schema_version": 1,
            "model_version": "fifo-v0.1",
            "evidence": evidence.model_dump(mode="json"),
            "parameter_basis": {
                "templates": "synthetic" if evidence.synthetic else evidence.template_basis,
                "assumptions": "assumed",
                "scenarios": "assumed",
                "calendars": "assumed",
                "reviewer_calendars": "assumed",
                "bounds": "assumed",
                "fixed_horizon_seconds": "assumed",
                "backlog_threshold": "assumed",
                "root_seed": "assumed",
                "replications": "assumed",
            },
            "coverage": {"training_weeks": len({week.week_start for week in experiment.templates})},
            "unsupported": {
                name: {"value": None, "reason": "unsupported_in_v0_1"}
                for name in ("defect_escape_rate", "security_risk_change", "policy_safety")
            },
        },
    )
    values: dict[tuple[str, str, str], list[Metric]] = defaultdict(list)
    deltas: dict[tuple[str, str], tuple[list[Metric], list[Metric]]] = {}
    limitations: set[str] = set()
    run = run_experiment(experiment)
    previous_baseline: tuple[str, int] | None = None
    with (
        (stage / "replications.jsonl").open("w", encoding="utf-8") as replications,
        (stage / "paired-deltas.jsonl").open("w", encoding="utf-8") as pairs,
        (stage / "traces.jsonl").open("w", encoding="utf-8") as traces,
    ):
        for row in run:
            identity = {
                "schema_version": 1,
                "synthetic": evidence.synthetic,
                "assumption": row.assumption_id,
                "scenario": row.scenario_id,
                "replication": row.replication,
            }
            # Serialize each pair directly, without copying or retaining sampled PR states.
            _line(
                replications,
                {
                    **identity,
                    "baseline": TypeAdapter(type(row.baseline)).dump_python(row.baseline),
                    "result": TypeAdapter(type(row.scenario)).dump_python(row.scenario),
                    "limitations": row.limitations,
                },
            )
            absolute = Metric(row.merge_delta, "engine_truncated" if row.merge_delta is None else None)
            relative = (
                Metric(None, "engine_truncated")
                if row.merge_delta is None
                else Metric(row.merge_delta / row.baseline.merges)
                if row.baseline.merges
                else Metric(None, "zero_baseline")
            )
            _line(
                pairs,
                {
                    **identity,
                    "absolute": TypeAdapter(Metric).dump_python(absolute),
                    "relative": TypeAdapter(Metric).dump_python(relative),
                },
            )
            absolute_values, relative_values = deltas.setdefault((row.assumption_id, row.scenario_id), ([], []))
            absolute_values.append(absolute)
            relative_values.append(relative)
            sides = [(row.scenario_id, row.scenario)] if row.scenario_id != "baseline" else []
            baseline_key = (row.assumption_id, row.replication)
            if baseline_key != previous_baseline:
                sides.append(("baseline", row.baseline))
                previous_baseline = baseline_key
            for scenario, counts in sides:
                if counts.engine_truncated:
                    limitations.add("engine_truncated")
                for level in ("all_work", "new_ready"):
                    dictionary = getattr(counts.metrics, level) if counts.metrics is not None else None
                    for name, sample in _metrics(dictionary).items():
                        values[(row.assumption_id, scenario, f"{level}.{name}")].append(sample)
            limitations.update(limit.split(":", 1)[0] for limit in row.limitations)
            if row.trace is not None:
                _line(
                    traces,
                    {**identity, "diagnostics": TypeAdapter(type(row.trace)).dump_python(row.trace, mode="json")},
                )
    rows = []
    for (assumption, scenario, metric), samples in sorted(values.items()):
        defined = [sample.value for sample in samples if sample.value is not None]
        rows.append(
            SummaryRow(
                assumption=assumption,
                scenario=scenario,
                metric=metric,
                summary=summarize_metrics(samples),
                event_probability=wilson(int(sum(defined)), len(defined))
                if metric.endswith(".backlog_exceeded")
                else None,
            )
        )
    comparisons = []
    for (assumption, scenario), (absolute_values, relative_values) in sorted(deltas.items()):
        defined = [sample.value for sample in absolute_values if sample.value is not None]
        comparisons.append(
            Comparison(
                assumption=assumption,
                scenario=scenario,
                absolute=summarize_metrics(absolute_values),
                relative=summarize_metrics(relative_values),
                more_merges=wilson(sum(value > 0 for value in defined), len(defined)),
            )
        )
    summary = Summary(
        evidence=evidence,
        requested_replications=experiment.replications,
        comparison_incomplete=run.comparison_incomplete,
        limitations=sorted(limitations),
        rows=rows,
        comparisons=comparisons,
    )
    _write(stage / "summary.json", summary.model_dump(mode="json"))
    with (stage / "summary.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "synthetic",
                "assumption",
                "scenario",
                "metric",
                "total",
                "defined",
                "excluded",
                "median",
                "low",
                "high",
                "reason",
            )
        )
        for item in rows:
            stats = item.summary
            writer.writerow(
                (
                    evidence.synthetic,
                    spreadsheet(item.assumption),
                    spreadsheet(item.scenario),
                    item.metric,
                    stats.total,
                    stats.defined,
                    stats.excluded,
                    stats.median.value,
                    stats.low.value,
                    stats.high.value,
                    stats.median.reason,
                )
            )
    (stage / "report.md").write_text(render_report(stage), encoding="utf-8")
    content_hashes = {}
    for path in sorted(stage.iterdir()):
        with path.open("rb") as source:
            content_hashes[path.name] = hashlib.file_digest(source, "sha256").hexdigest()
    _write(
        stage / "manifest.json",
        {
            **evidence.model_dump(mode="json"),
            "application_version": __version__,
            "model_version": "fifo-v0.1",
            "timezone": experiment.timezone,
            "root_seed": experiment.root_seed,
            "rng_scheme": (
                "SHA-256 canonical ASCII JSON string keys / SeedSequence / PCG64; scenario-independent latent keys"
            ),
            "dependency_versions": {
                name: version(name) for name in ("numpy", "simpy", "pydantic", "httpx", "pyyaml", "typer")
            },
            "python_version": platform.python_version(),
            "content_hashes": content_hashes,
            "dataset_content_hash": hashlib.sha256(_json(resolved["templates"]).encode("utf-8")).hexdigest(),
        },
    )


def write_experiment(experiment: Experiment, evidence: Evidence, out: Path, *, overwrite: bool = False) -> None:
    """Publish only a complete bundle; explicit overwrite stages before moving old data.

    Single-writer local API. An overwrite has a brief directory-name gap, but
    never exposes partial files. Failures during publication restore the old name.
    """
    if out.is_symlink() or (out.exists() and not out.is_dir()):
        raise ValueError("output must be a directory, not a file or symlink")
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise FileExistsError("nonempty output directory; explicitly request overwrite")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    backup = stage.with_name(stage.name + "-previous")
    try:
        _bundle(experiment, evidence, stage)
        # Backup must be outside the published directory.
        if out.exists():
            out.rename(backup)
        try:
            stage.rename(out)
        except OSError:
            if backup.exists():
                backup.rename(out)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    if backup.exists():
        shutil.rmtree(backup)
