"""Resolve persisted calibration/configuration contracts into local experiments."""

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import TypeAdapter, ValidationError

from merge_carlo.artifacts import ArtifactLineage, Evidence, rewrite_report_in_bundle, write_experiment
from merge_carlo.calibration import Basis, CalibratedModel, DurationDistribution, Parameter
from merge_carlo.configuration import (
    CalendarConfig,
    ExecutionConfig,
    ScenarioConfig,
    ScenarioEntryConfig,
    load_scenario_config,
)
from merge_carlo.reporting import render_report, write_report
from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI
from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, WeeklyWindow, materialize_run_bounds
from merge_carlo.simulation.engine import ReviewBypass
from merge_carlo.simulation.runner import AssumptionSet, Experiment, Scenario, ServiceDistribution
from merge_carlo.validation import ValidationResult

_MAX_JSON_BYTES = 16 * 1024 * 1024
_MAX_MODEL_TEMPLATES = 1_000
_MAX_MODEL_ARRIVALS = 1_000_000
_MAX_MODEL_PARAMETERS = 1_000
_MAX_PARAMETER_VALUES = 100_000
_SUPPORTED_MODEL_VERSION = "fifo-v0.1"
_DURATION_ADAPTER: TypeAdapter[DurationDistribution] = TypeAdapter(DurationDistribution)
_MODEL_FIELDS = frozenset(field.name for field in fields(CalibratedModel))
_UNAVAILABLE_FIELDS = frozenset(("value", "reason"))
_ARRIVAL_FIELDS = frozenset(("offset", "author_id", "origin"))
_WEEK_FIELDS = frozenset(("week_start", "arrivals"))
_PARAMETER_FIELDS = frozenset(
    (
        "name",
        "value_specification",
        "unit",
        "basis",
        "sample_count",
        "missingness_treatment",
        "grouping_rule",
        "fallback_rule",
        "evidence_references",
        "confidence_interval",
    )
)


@dataclass(frozen=True, slots=True)
class ModelSource:
    """Validated model plus the canonical content hash used for lineage."""

    model: CalibratedModel
    content_hash: str
    parameter_provenance: tuple[tuple[str, Basis], ...]


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def _read_json(path: Path, *, label: str) -> tuple[object, bytes]:
    try:
        payload = path.read_bytes()
    except OSError:
        raise ValueError(f"invalid {label} artifact") from None
    if len(payload) > _MAX_JSON_BYTES:
        raise ValueError(f"{label} artifact exceeds 16 MiB")
    try:
        return json.loads(payload), payload
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(f"invalid {label} artifact") from None


def _exact_keys(value: object, expected: frozenset[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"invalid {label} contract")
    return cast(dict[str, object], value)


def _validate_model_shape(data: object) -> dict[str, object]:
    root = _exact_keys(data, _MODEL_FIELDS, "model")
    if type(root.get("schema_version")) is not int or root["schema_version"] != 1:
        raise ValueError("unsupported model schema version")
    for name in ("seed", "rng_scheme", "reviewer_roster", "initialization_scheme"):
        _exact_keys(root[name], _UNAVAILABLE_FIELDS, f"model.{name}")
    templates = root["arrival_templates"]
    if not isinstance(templates, list) or len(templates) > _MAX_MODEL_TEMPLATES:
        raise ValueError("invalid model.arrival_templates contract")
    arrival_count = 0
    for index, template in enumerate(templates):
        week = _exact_keys(template, _WEEK_FIELDS, f"model.arrival_templates[{index}]")
        arrivals = week["arrivals"]
        if not isinstance(arrivals, list) or len(arrivals) > _MAX_MODEL_ARRIVALS:
            raise ValueError("invalid model arrival list")
        arrival_count += len(arrivals)
        if arrival_count > _MAX_MODEL_ARRIVALS:
            raise ValueError("model arrivals exceed the resource limit")
        for arrival_index, arrival in enumerate(arrivals):
            _exact_keys(arrival, _ARRIVAL_FIELDS, f"model.arrival_templates[{index}].arrivals[{arrival_index}]")
    parameters = root["parameters"]
    if not isinstance(parameters, list) or len(parameters) > _MAX_MODEL_PARAMETERS:
        raise ValueError("invalid model.parameters contract")
    for index, parameter in enumerate(parameters):
        item = _exact_keys(parameter, _PARAMETER_FIELDS, f"model.parameters[{index}]")
        _exact_keys(item["confidence_interval"], _UNAVAILABLE_FIELDS, f"model.parameters[{index}].confidence_interval")
        specification = item["value_specification"]
        if (
            isinstance(specification, dict)
            and isinstance(specification.get("seconds"), list)
            and len(specification["seconds"]) > _MAX_PARAMETER_VALUES
        ):
            raise ValueError("model parameter values exceed the resource limit")
        if isinstance(specification, dict) and specification.get("kind") in {"constant", "lognormal", "empirical"}:
            try:
                _DURATION_ADAPTER.validate_json(_canonical(specification), strict=True)
            except (TypeError, ValidationError, ValueError):
                raise ValueError(f"invalid model.parameters[{index}].value_specification contract") from None
    return root


def load_model(path: Path) -> ModelSource:
    """Load one bounded, versioned, strict calibration model artifact."""
    data, payload = _read_json(path, label="model")
    root = _validate_model_shape(data)
    try:
        model = TypeAdapter(CalibratedModel).validate_json(payload, strict=True)
    except (TypeError, ValidationError, ValueError):
        raise ValueError("invalid model artifact") from None
    if type(model.schema_version) is not int or model.schema_version != 1:
        raise ValueError("unsupported model schema version")
    if model.training_cutoff.tzinfo is None or model.training_cutoff.utcoffset() != timedelta(0):
        raise ValueError("model training_cutoff must be an aware UTC datetime")
    if model.model_version != _SUPPORTED_MODEL_VERSION:
        raise ValueError("unsupported model version")
    names = tuple(parameter.name for parameter in model.parameters)
    if len(set(names)) != len(names):
        raise ValueError("model parameter names must be unique")
    provenance = tuple((parameter.name, parameter.basis) for parameter in model.parameters)
    return ModelSource(model, hashlib.sha256(_canonical(root)).hexdigest(), provenance)


def _service_distribution(parameters: tuple[Parameter, ...]) -> ServiceDistribution:
    effort = next((parameter for parameter in parameters if parameter.name == "review_effort.human"), None)
    if effort is None:
        raise ValueError("model is missing review_effort.human")
    specification = effort.value_specification
    kind = specification.get("kind")
    if kind == "constant":
        value = specification.get("seconds")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("model review_effort.human has an invalid duration")
        return ServiceDistribution("constant", (float(value),))
    if kind == "lognormal":
        median_seconds = specification.get("median_seconds")
        sigma = specification.get("sigma")
        if (
            isinstance(median_seconds, bool)
            or not isinstance(median_seconds, (int, float))
            or isinstance(sigma, bool)
            or not isinstance(sigma, (int, float))
        ):
            raise ValueError("model review_effort.human has an invalid lognormal duration")
        return ServiceDistribution("lognormal", (float(median_seconds), float(sigma)))
    if kind == "empirical":
        values = specification.get("seconds")
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError("model review_effort.human has an invalid empirical duration")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError("model review_effort.human has an invalid empirical duration")
        return ServiceDistribution("empirical", tuple(float(value) for value in values))
    raise ValueError("model review_effort.human has an unsupported duration distribution")


def _calendar(config: CalendarConfig) -> DutyCalendar:
    return DutyCalendar(
        config.timezone,
        tuple(WeeklyWindow(window.name, window.weekday, window.start, window.end) for window in config.windows),
        tuple(LocalAbsence(absence.start, absence.end) for absence in config.absences),
    )


def _calendar_map(config: ScenarioConfig) -> dict[str, DutyCalendar]:
    execution = config.execution
    declared = list(execution.calendars if execution is not None else ())
    if not declared:
        declared = [calendar for scenario in config.scenarios for calendar in scenario.calendars]
    calendars: dict[str, DutyCalendar] = {}
    for item in declared:
        value = _calendar(item)
        prior = calendars.setdefault(item.name, value)
        if prior != value:
            raise ValueError(f"conflicting calendar definition: {item.name}")
    return calendars


def _reviewer_calendars(config: ScenarioConfig, calendars: dict[str, DutyCalendar]) -> tuple[tuple[str, str], ...]:
    execution = config.execution
    if execution is not None and execution.reviewers:
        return tuple((reviewer.name, reviewer.calendar) for reviewer in execution.reviewers)
    reviewers = sorted({absence.reviewer for scenario in config.scenarios for absence in scenario.absences})
    if not calendars:
        if reviewers:
            raise ValueError("scenario absences require a declared reviewer calendar")
        return ()
    default_calendar = sorted(calendars)[0]
    return tuple((reviewer, default_calendar) for reviewer in reviewers) or (("reviewer", default_calendar),)


def _scenario(entry: ScenarioEntryConfig) -> Scenario:
    demand = None
    if entry.demand is not None:
        demand = (
            AdditiveAI(entry.demand.fraction)
            if entry.demand.kind == "additive_ai"
            else ReplacementAI(entry.demand.fraction)
        )
    bypass = None if entry.bypass is None else ReviewBypass(entry.bypass.eligible_fraction, entry.bypass.audit_fraction)
    calendars = tuple((calendar.name, _calendar(calendar)) for calendar in entry.calendars)
    absences = tuple(
        (item.reviewer, tuple(LocalAbsence(absence.start, absence.end) for absence in item.absences))
        for item in entry.absences
    )
    return Scenario(entry.name, demand=demand, calendars=calendars, absences=absences, bypass=bypass)


def _execution(model: CalibratedModel, config: ScenarioConfig) -> ExecutionConfig:
    if config.execution is not None:
        return config.execution
    try:
        zone = ZoneInfo(model.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("model has an invalid timezone") from None
    local_cutoff = model.training_cutoff.astimezone(zone)
    return ExecutionConfig(observation_start=datetime.combine(local_cutoff.date(), time()))


def build_experiment(source: ModelSource, config: ScenarioConfig) -> Experiment:
    """Resolve model arrivals and strict scenario/run inputs without file I/O."""
    execution = _execution(source.model, config)
    if execution.observation_start is None:
        raise ValueError("execution observation_start is required")
    bounds = materialize_run_bounds(
        execution.observation_start,
        source.model.timezone,
        horizon_days=execution.horizon_days,
        warmup_days=execution.warmup_days,
    )
    calendars = _calendar_map(config)
    reviewer_calendars = _reviewer_calendars(config, calendars)
    scenarios = tuple(_scenario(entry) for entry in config.scenarios)
    calendar_names = set(calendars)
    reviewer_names = {name for name, _ in reviewer_calendars}
    for scenario in scenarios:
        if set(name for name, _ in scenario.calendars) - calendar_names:
            raise ValueError("scenario calendar override is not declared by execution")
        if set(name for name, _ in scenario.absences) - reviewer_names:
            raise ValueError("scenario absence reviewer is not declared by execution")
    distribution = _service_distribution(source.model.parameters)
    assumption = AssumptionSet("base", distribution.reference_seconds, service_distribution=distribution)
    return Experiment(
        templates=source.model.arrival_templates,
        timezone=source.model.timezone,
        bounds=bounds,
        calendars=tuple(sorted(calendars.items())),
        reviewer_calendars=tuple(sorted(reviewer_calendars)),
        assumptions=(assumption,),
        scenarios=scenarios,
        root_seed=execution.root_seed,
        replications=execution.replications,
        trace_replications=execution.trace_replications,
        fixed_horizon_seconds=execution.fixed_horizon_seconds,
        backlog_threshold=execution.backlog_threshold,
    )


def _lineage(source: ModelSource) -> ArtifactLineage:
    return ArtifactLineage(
        dataset_content_hash=source.model.dataset_content_hash,
        model_content_hash=source.content_hash,
        model_version=source.model.model_version,
        parameter_provenance=dict(source.parameter_provenance),
        readiness_policy=source.model.readiness_policy,
        evidence_status=source.model.evidence_status,
    )


def simulate(model_path: Path, scenarios_path: Path, out: Path, *, overwrite: bool = False) -> None:
    """Publish a reproducible experiment bundle from persisted inputs."""
    source = load_model(model_path)
    config = load_scenario_config(scenarios_path)
    experiment = build_experiment(source, config)
    model = source.model
    evidence = Evidence(
        synthetic=model.evidence_status == "synthetic_demonstration",
        training_cutoff=model.training_cutoff.isoformat(),
        template_basis="derived" if model.evidence_status != "synthetic_demonstration" else "assumed",
    )
    write_experiment(experiment, evidence, out, overwrite=overwrite, lineage=_lineage(source))


def _validation(path: Path) -> ValidationResult:
    data, payload = _read_json(path, label="validation")
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported validation schema version")
    try:
        return ValidationResult.model_validate_json(payload)
    except (TypeError, ValidationError, ValueError):
        raise ValueError("invalid validation artifact") from None


def _check_lineage(results: Path, validation: ValidationResult) -> None:
    manifest_data, _ = _read_json(results / "manifest.json", label="results manifest")
    if not isinstance(manifest_data, dict):
        raise ValueError("invalid results manifest contract")
    manifest = cast(dict[str, object], manifest_data)
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("unsupported results manifest schema version")
    source_model_hash = manifest.get("source_model_content_hash")
    source_model_version = manifest.get("source_model_version")
    dataset_hash = manifest.get("dataset_content_hash")
    if (
        not isinstance(source_model_hash, str)
        or not isinstance(source_model_version, str)
        or not isinstance(dataset_hash, str)
    ):
        raise ValueError("results manifest is missing model lineage")
    if any(
        len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
        for value in (source_model_hash, dataset_hash)
    ):
        raise ValueError("results manifest is missing model lineage")
    if validation.model_version != source_model_version or validation.dataset_content_hash != dataset_hash:
        raise ValueError("validation and results lineage do not match")
    if (
        len(validation.model_content_hash) != 64
        or any(character not in "0123456789abcdef" for character in validation.model_content_hash)
        or validation.model_content_hash == "0" * 64
    ):
        raise ValueError("validation artifact has an unbound model content hash")


def report(results: Path, validation: Path, out: Path, *, overwrite: bool = False) -> None:
    """Render saved results and validation without running the simulation."""
    evidence = _validation(validation)
    _check_lineage(results, evidence)
    text = render_report(results, validation_status=evidence.status)
    if out.is_symlink():
        raise ValueError("report output must not be a symlink")
    if out.resolve(strict=False) == (results / "report.md").resolve(strict=False):
        rewrite_report_in_bundle(results, text, overwrite=overwrite, validation_status=evidence.status)
    else:
        write_report(text, out, overwrite=overwrite)
