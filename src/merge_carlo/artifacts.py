"""Stream experiment artifacts into a staged, versioned local directory."""

import csv
import hashlib
import json
import platform
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass, fields
from importlib.metadata import version
from pathlib import Path
from typing import Literal, TextIO

from pydantic import TypeAdapter

from merge_carlo import __version__
from merge_carlo.reporting import Comparison, ReplicationCount, Summary, SummaryRow, render_report, wilson, write_report
from merge_carlo.reporting import Evidence as Evidence
from merge_carlo.simulation.arrivals import AdditiveAI
from merge_carlo.simulation.metrics import HorizonShare, Metric, MetricDictionary, summarize_metrics
from merge_carlo.simulation.runner import Experiment, run_experiment

DEPENDENCY_NAMES = ("numpy", "simpy", "pydantic", "httpx", "pyyaml", "typer")


@dataclass(frozen=True, slots=True)
class ArtifactLineage:
    """Upstream model and dataset identity carried into experiment artifacts."""

    dataset_content_hash: str
    model_content_hash: str
    model_version: str
    parameter_provenance: dict[str, str]
    readiness_policy: str
    evidence_status: str

    def __post_init__(self) -> None:
        for name, value in (("dataset", self.dataset_content_hash), ("model", self.model_content_hash)):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"invalid {name} content hash")
        if not self.model_version or not self.readiness_policy or not self.evidence_status:
            raise ValueError("artifact lineage metadata must not be empty")

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_content_hash": self.dataset_content_hash,
            "model_content_hash": self.model_content_hash,
            "model_version": self.model_version,
            "parameter_provenance": dict(sorted(self.parameter_provenance.items())),
            "readiness_policy": self.readiness_policy,
            "evidence_status": self.evidence_status,
        }


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


def _bundle(experiment: Experiment, evidence: Evidence, stage: Path, lineage: ArtifactLineage | None = None) -> None:
    resolved = TypeAdapter(Experiment).dump_python(experiment, mode="json")
    for assumption in resolved["assumptions"]:
        if assumption.get("service_distribution") is None:
            del assumption["service_distribution"]
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
    if lineage is not None:
        configuration["source_lineage"] = lineage.as_dict()
    _write(stage / "resolved-scenarios.json", configuration)
    card = {
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
    }
    if lineage is not None:
        card["parameter_provenance"] = dict(sorted(lineage.parameter_provenance.items()))
        card["source_lineage"] = lineage.as_dict()
    _write(stage / "model-card.json", card)
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
        replication_counts=[
            ReplicationCount(
                assumption=assumption,
                scenario=scenario,
                requested=experiment.replications,
                usable=counts.valid_replications,
                engine_truncated=counts.engine_truncated_count,
            )
            for (assumption, scenario), counts in sorted(run.summaries.items())
        ],
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
    manifest: dict[str, object] = {
        **evidence.model_dump(mode="json"),
        "application_version": __version__,
        "model_version": "fifo-v0.1",
        "timezone": experiment.timezone,
        "root_seed": experiment.root_seed,
        "rng_scheme": (
            "SHA-256 canonical ASCII JSON string keys / SeedSequence / PCG64; scenario-independent latent keys"
        ),
        "dependency_versions": {name: version(name) for name in DEPENDENCY_NAMES},
        "python_version": platform.python_version(),
        "content_hashes": content_hashes,
        "dataset_content_hash": hashlib.sha256(_json(resolved["templates"]).encode("utf-8")).hexdigest(),
    }
    if lineage is not None:
        manifest.update(
            {
                "source_model_content_hash": lineage.model_content_hash,
                "source_model_version": lineage.model_version,
                "source_readiness_policy": lineage.readiness_policy,
                "source_evidence_status": lineage.evidence_status,
                "source_dataset_content_hash": lineage.dataset_content_hash,
                "template_content_hash": manifest["dataset_content_hash"],
                "dataset_content_hash": lineage.dataset_content_hash,
            }
        )
    _write(stage / "manifest.json", manifest)


def write_experiment(
    experiment: Experiment,
    evidence: Evidence,
    out: Path,
    *,
    overwrite: bool = False,
    lineage: ArtifactLineage | None = None,
) -> None:
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
        _bundle(experiment, evidence, stage, lineage)
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


def rewrite_report_in_bundle(
    results: Path,
    text: str,
    *,
    overwrite: bool = False,
    validation_status: Literal["not_performed", "pass", "fail", "insufficient_evidence"] | None = None,
) -> None:
    """Replace an in-bundle report while keeping its manifest hash current."""
    if results.is_symlink() or not results.is_dir():
        raise ValueError("results must be a directory, not a symlink or file")
    report = results / "report.md"
    if report.exists() and not overwrite:
        raise FileExistsError("nonempty report output; explicitly request overwrite")
    results.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f".{results.name}-report-", dir=results.parent))
    stage = staging_root / "bundle"
    backup = staging_root / "previous"
    try:
        shutil.copytree(results, stage)
        write_report(text, stage / "report.md", overwrite=True)
        manifest_path = stage / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1
            or not isinstance(manifest.get("content_hashes"), dict)
        ):
            raise ValueError("invalid results manifest contract")
        hashes = manifest["content_hashes"]
        hashes["report.md"] = hashlib.sha256((stage / "report.md").read_bytes()).hexdigest()
        if validation_status is not None:
            manifest["validation_status"] = validation_status
        _write(manifest_path, manifest)
        results.rename(backup)
        try:
            stage.rename(results)
        except OSError:
            backup.rename(results)
            raise
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
