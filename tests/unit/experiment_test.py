"""Persisted model/configuration experiment and report workflow."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from typer.testing import CliRunner

import merge_carlo.experiment as experiment_module
from merge_carlo.calibration import CalibratedModel, Parameter, Unavailable
from merge_carlo.cli import app
from merge_carlo.configuration import (
    AbsenceConfig,
    AdditiveDemandConfig,
    CalendarConfig,
    ExecutionConfig,
    ReplacementDemandConfig,
    ReviewBypassConfig,
    ReviewerAbsencesConfig,
    ReviewerConfig,
    ScenarioConfig,
    ScenarioEntryConfig,
    WeeklyWindowConfig,
)
from merge_carlo.experiment import (
    ModelSource,
    _calendar,
    _calendar_map,
    _canonical,
    _check_lineage,
    _exact_keys,
    _execution,
    _read_json,
    _reviewer_calendars,
    _scenario,
    _service_distribution,
    _validate_model_shape,
    _validation,
    build_experiment,
    load_model,
)
from merge_carlo.reporting import write_report
from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI, TemplateArrival, WeekTemplate
from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, WeeklyWindow
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.simulation.engine import ReviewBypass
from merge_carlo.simulation.runner import ServiceDistribution
from merge_carlo.validation import Estimate, ValidationResult

pytestmark = pytest.mark.unit


def model() -> CalibratedModel:
    return CalibratedModel(
        schema_version=1,
        model_version="fifo-v0.1",
        feature_version="features-v1",
        training_cutoff=datetime(2026, 9, 1, tzinfo=UTC),
        timezone="UTC",
        dataset_content_hash="a" * 64,
        assumptions_content_hash="b" * 64,
        application_version="0.1.0",
        python_version="3.12.0",
        dependency_versions={"numpy": "1"},
        seed=Unavailable(None, "not_applicable_to_calibration"),
        rng_scheme=Unavailable(None, "not_applicable_to_calibration"),
        reviewer_roster=Unavailable(None, "downstream_simulation_input"),
        initialization_scheme=Unavailable(None, "downstream_simulation_input"),
        readiness_policy="strict",
        evidence_status="empirically_informed",
        evidence_flags=(),
        arrival_templates=(
            WeekTemplate(
                date(2026, 9, 7),
                (TemplateArrival(timedelta(days=1, hours=1), "author", WorkOrigin.HUMAN),),
            ),
        ),
        parameters=(
            Parameter(
                "review_effort.human",
                {"kind": "constant", "seconds": 10.0},
                "active_service_seconds",
                "assumed",
                0,
                "operator supplied",
                "declared human cohort",
                "none",
                ("calibration_assumptions.review_effort",),
                Unavailable(None, "not_declared"),
            ),
        ),
    )


def write_model(path: Path, value: CalibratedModel | None = None) -> None:
    path.write_text(
        json.dumps(TypeAdapter(CalibratedModel).dump_python(value or model(), mode="json"), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_scenarios(path: Path) -> None:
    path.write_text(
        """schema_version: 1
execution:
  observation_start: 2026-09-08T00:00:00
  horizon_days: 1
  warmup_days: 1
  root_seed: 7
  replications: 2
  calendars:
    - name: duty
      timezone: UTC
      windows:
        - name: tuesday
          weekday: 1
          start: "00:00:00"
          end: "02:00:00"
  reviewers:
    - name: reviewer
      calendar: duty
scenarios:
  - name: additive
    demand:
      kind: additive_ai
      fraction: 0.5
""",
        encoding="utf-8",
    )


def model_payload() -> dict[str, object]:
    payload = TypeAdapter(CalibratedModel).dump_python(model(), mode="json")
    assert isinstance(payload, dict)
    return payload


def calendar_config(
    name: str = "duty",
    *,
    windows: tuple[WeeklyWindowConfig, ...] | None = None,
    absences: tuple[AbsenceConfig, ...] = (),
) -> CalendarConfig:
    if windows is None:
        windows = (WeeklyWindowConfig(name="morning", weekday=1, start=time(1), end=time(2)),)
    return CalendarConfig(name=name, timezone="UTC", windows=windows, absences=absences)


def effort_parameter(specification: dict[str, object]) -> Parameter:
    return replace(model().parameters[0], value_specification=specification)


def validation(model_hash: str) -> ValidationResult:
    return ValidationResult(
        status="pass",
        protocol="held_out",
        model_version="fifo-v0.1",
        dataset_content_hash="a" * 64,
        model_content_hash=model_hash,
        replay_arrivals_content_hash="c" * 64,
        training_cutoff=datetime(2026, 9, 1, tzinfo=UTC),
        validation_interval_start=datetime(2026, 9, 8, tzinfo=UTC),
        validation_interval_end=datetime(2026, 9, 9, tzinfo=UTC),
        thresholds={},
        observed_mature_pull_requests=1,
        replay_replications=1,
        evidence_flags=(),
        gates=(),
        benchmark_label="descriptive_reference_not_intervention_model",
        benchmark_capacity_queue=False,
        benchmark_observations_content_hash="d" * 64,
        benchmark_completion_categories=(),
        benchmark_comparison=(),
        initialization_discrepancy=Estimate(value=0, low=0, high=0, sample_size=1),
        absolute_backlog_forecast_supported=False,
        unsupported={"policy_safety": Unavailable(None, "unsupported_in_v0_1")},
        structural_fit_limitations=(
            "multiple_required_approvals",
            "reviewer_routing",
            "merge_queues",
            "full_branch_protection",
        ),
    )


def test_simulate_resolves_contracts_and_propagates_lineage(tmp_path: Path) -> None:
    model_path, scenarios_path, out = tmp_path / "model.json", tmp_path / "scenarios.yaml", tmp_path / "out"
    write_model(model_path)
    write_scenarios(scenarios_path)

    result = CliRunner().invoke(
        app,
        ["simulate", "--model", str(model_path), "--scenarios", str(scenarios_path), "--out", str(out)],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["dataset_content_hash"] == "a" * 64
    assert manifest["source_model_version"] == "fifo-v0.1"
    assert manifest["source_model_content_hash"]
    card = json.loads((out / "model-card.json").read_text())
    assert card["parameter_provenance"]["review_effort.human"] == "assumed"
    resolved = json.loads((out / "resolved-scenarios.json").read_text())
    assert resolved["experiment"]["bounds"]["observation"]["start"] == "2026-09-08T00:00:00Z"
    assert resolved["demand_kinds"] == {"additive": "additive"}


def test_simulate_is_semantically_reproducible_and_rejects_invalid_inputs(tmp_path: Path) -> None:
    model_path, scenarios_path = tmp_path / "model.json", tmp_path / "scenarios.yaml"
    write_model(model_path)
    write_scenarios(scenarios_path)
    first, second = tmp_path / "first", tmp_path / "second"
    runner = CliRunner()
    args = ["simulate", "--model", str(model_path), "--scenarios", str(scenarios_path)]
    assert runner.invoke(app, [*args, "--out", str(first)]).exit_code == 0
    assert runner.invoke(app, [*args, "--out", str(second)]).exit_code == 0
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }

    bad_model = tmp_path / "bad-model.json"
    write_model(bad_model)
    payload = json.loads(bad_model.read_text())
    payload["unknown"] = True
    bad_model.write_text(json.dumps(payload))
    failure = runner.invoke(app, [*args, "--model", str(bad_model), "--out", str(tmp_path / "bad")])
    assert failure.exit_code == 2
    assert "invalid" in failure.output.lower()

    bad_version = tmp_path / "bad-version.json"
    write_model(bad_version)
    bad_version_payload = json.loads(bad_version.read_text())
    bad_version_payload["schema_version"] = True
    bad_version.write_text(json.dumps(bad_version_payload), encoding="utf-8")
    failure = runner.invoke(app, [*args, "--model", str(bad_version), "--out", str(tmp_path / "bad-version")])
    assert failure.exit_code == 2

    bad_model_version = tmp_path / "bad-model-version.json"
    write_model(bad_model_version, replace(model(), model_version="other-v0.1"))
    failure = runner.invoke(
        app, [*args, "--model", str(bad_model_version), "--out", str(tmp_path / "bad-model-version")]
    )
    assert failure.exit_code == 2

    bad_parameter = tmp_path / "bad-parameter.json"
    write_model(bad_parameter)
    bad_parameter_payload = json.loads(bad_parameter.read_text())
    bad_parameter_payload["parameters"][0]["sample_count"] = True
    bad_parameter.write_text(json.dumps(bad_parameter_payload), encoding="utf-8")
    failure = runner.invoke(app, [*args, "--model", str(bad_parameter), "--out", str(tmp_path / "bad-parameter")])
    assert failure.exit_code == 2

    bad_distribution = tmp_path / "bad-distribution.json"
    write_model(bad_distribution)
    bad_distribution_payload = json.loads(bad_distribution.read_text())
    bad_distribution_payload["parameters"][0]["value_specification"]["unknown"] = True
    bad_distribution.write_text(json.dumps(bad_distribution_payload), encoding="utf-8")
    failure = runner.invoke(app, [*args, "--model", str(bad_distribution), "--out", str(tmp_path / "bad-distribution")])
    assert failure.exit_code == 2

    naive_cutoff = tmp_path / "naive-cutoff.json"
    write_model(naive_cutoff, replace(model(), training_cutoff=datetime(2026, 9, 1)))
    failure = runner.invoke(app, [*args, "--model", str(naive_cutoff), "--out", str(tmp_path / "naive-cutoff")])
    assert failure.exit_code == 2

    bad_scenarios = tmp_path / "bad-scenarios.yaml"
    bad_scenarios.write_text(
        scenarios_path.read_text().replace("schema_version: 1", "schema_version: true", 1), encoding="utf-8"
    )
    failure = runner.invoke(
        app,
        [
            "simulate",
            "--model",
            str(model_path),
            "--scenarios",
            str(bad_scenarios),
            "--out",
            str(tmp_path / "bad-scenarios"),
        ],
    )
    assert failure.exit_code == 2

    oversized = tmp_path / "oversized.yaml"
    oversized.write_text(scenarios_path.read_text().replace("replications: 2", "replications: 10001"), encoding="utf-8")
    failure = runner.invoke(
        app,
        ["simulate", "--model", str(model_path), "--scenarios", str(oversized), "--out", str(tmp_path / "oversized")],
    )
    assert failure.exit_code == 2

    nonconstant = tmp_path / "nonconstant.json"
    effort = replace(
        model().parameters[0],
        value_specification={"kind": "lognormal", "median_seconds": 10.0, "sigma": 0.5},
    )
    write_model(nonconstant, replace(model(), parameters=(effort,)))
    nonconstant_out = tmp_path / "nonconstant"
    failure = runner.invoke(app, [*args, "--model", str(nonconstant), "--out", str(nonconstant_out)])
    assert failure.exit_code == 0, failure.output
    resolved = json.loads((nonconstant_out / "resolved-scenarios.json").read_text())
    distribution = resolved["experiment"]["assumptions"][0]["service_distribution"]
    assert distribution["kind"] == "lognormal"
    assert distribution["parameters"] == [10.0, 0.5]

    subsecond = tmp_path / "subsecond.json"
    effort = replace(model().parameters[0], value_specification={"kind": "constant", "seconds": 0.5})
    write_model(subsecond, replace(model(), parameters=(effort,)))
    subsecond_out = tmp_path / "subsecond"
    success = runner.invoke(app, [*args, "--model", str(subsecond), "--out", str(subsecond_out)])
    assert success.exit_code == 0, success.output
    subsecond_resolved = json.loads((subsecond_out / "resolved-scenarios.json").read_text())
    assert subsecond_resolved["experiment"]["assumptions"][0]["service_seconds"] == 1


def test_canonical_json_is_stable_and_rejects_nonfinite_values() -> None:
    assert _canonical({"é": {"z": 2, "a": 1}}) == b'{"\\u00e9":{"a":1,"z":2}}'
    with pytest.raises(ValueError):
        _canonical({"value": float("nan")})


def test_bounded_json_reader_enforces_size_and_parse_contracts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(experiment_module, "_MAX_JSON_BYTES", 2)
    valid = tmp_path / "valid.json"
    valid.write_bytes(b"{}")
    assert _read_json(valid, label="sample") == ({}, b"{}")

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{}x")
    with pytest.raises(ValueError, match="sample artifact exceeds 16 MiB"):
        _read_json(oversized, label="sample")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_bytes(b"[")
    with pytest.raises(ValueError, match="invalid sample artifact"):
        _read_json(invalid_json, label="sample")

    invalid_encoding = tmp_path / "invalid-encoding.json"
    invalid_encoding.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="invalid sample artifact"):
        _read_json(invalid_encoding, label="sample")

    with pytest.raises(ValueError, match="invalid sample artifact"):
        _read_json(tmp_path / "missing.json", label="sample")


def test_model_shape_validation_rejects_each_nested_contract() -> None:
    root = model_payload()
    invalid: list[tuple[dict[str, object], str]] = []

    unknown_root = model_payload()
    unknown_root["unknown"] = True
    invalid.append((unknown_root, "invalid model contract"))

    unsupported_schema = model_payload()
    unsupported_schema["schema_version"] = 2
    invalid.append((unsupported_schema, "unsupported model schema version"))

    unavailable = model_payload()
    seed = unavailable["seed"]
    assert isinstance(seed, dict)
    seed["extra"] = True
    invalid.append((unavailable, "invalid model.seed contract"))

    invalid_templates = model_payload()
    invalid_templates["arrival_templates"] = {}
    invalid.append((invalid_templates, "invalid model.arrival_templates contract"))

    invalid_week = model_payload()
    weeks = invalid_week["arrival_templates"]
    assert isinstance(weeks, list)
    assert isinstance(weeks[0], dict)
    weeks[0]["extra"] = True
    invalid.append((invalid_week, "invalid model.arrival_templates[0] contract"))

    invalid_arrivals = model_payload()
    weeks = invalid_arrivals["arrival_templates"]
    assert isinstance(weeks, list)
    assert isinstance(weeks[0], dict)
    weeks[0]["arrivals"] = {}
    invalid.append((invalid_arrivals, "invalid model arrival list"))

    invalid_arrival = model_payload()
    weeks = invalid_arrival["arrival_templates"]
    assert isinstance(weeks, list)
    assert isinstance(weeks[0], dict)
    arrivals = weeks[0]["arrivals"]
    assert isinstance(arrivals, list)
    assert isinstance(arrivals[0], dict)
    arrivals[0]["extra"] = True
    invalid.append((invalid_arrival, "invalid model.arrival_templates[0].arrivals[0] contract"))

    invalid_parameters = model_payload()
    invalid_parameters["parameters"] = {}
    invalid.append((invalid_parameters, "invalid model.parameters contract"))

    invalid_parameter = model_payload()
    parameters = invalid_parameter["parameters"]
    assert isinstance(parameters, list)
    assert isinstance(parameters[0], dict)
    parameters[0]["extra"] = True
    invalid.append((invalid_parameter, "invalid model.parameters[0] contract"))

    invalid_interval = model_payload()
    parameters = invalid_interval["parameters"]
    assert isinstance(parameters, list)
    assert isinstance(parameters[0], dict)
    interval = parameters[0]["confidence_interval"]
    assert isinstance(interval, dict)
    interval["extra"] = True
    invalid.append((invalid_interval, "invalid model.parameters[0].confidence_interval contract"))

    invalid_duration = model_payload()
    parameters = invalid_duration["parameters"]
    assert isinstance(parameters, list)
    assert isinstance(parameters[0], dict)
    parameters[0]["value_specification"] = {"kind": "constant", "seconds": "10"}
    invalid.append((invalid_duration, "invalid model.parameters[0].value_specification contract"))

    for value, message in invalid:
        with pytest.raises(ValueError) as error:
            _validate_model_shape(value)
        assert str(error.value) == message

    assert _validate_model_shape(root) == root


def test_model_shape_validation_enforces_resource_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = model_payload()
    monkeypatch.setattr(experiment_module, "_MAX_MODEL_TEMPLATES", 1)
    assert _validate_model_shape(payload) == payload
    payload["arrival_templates"] = [payload["arrival_templates"], payload["arrival_templates"]]
    with pytest.raises(ValueError, match="invalid model.arrival_templates contract"):
        _validate_model_shape(payload)

    payload = model_payload()
    monkeypatch.setattr(experiment_module, "_MAX_MODEL_ARRIVALS", 1)
    assert _validate_model_shape(payload) == payload
    weeks = payload["arrival_templates"]
    assert isinstance(weeks, list)
    assert isinstance(weeks[0], dict)
    weeks[0]["arrivals"] = [weeks[0]["arrivals"], weeks[0]["arrivals"]]
    with pytest.raises(ValueError, match="invalid model arrival list"):
        _validate_model_shape(payload)

    payload = model_payload()
    monkeypatch.setattr(experiment_module, "_MAX_MODEL_PARAMETERS", 1)
    assert _validate_model_shape(payload) == payload
    payload["parameters"] = [payload["parameters"], payload["parameters"]]
    with pytest.raises(ValueError, match="invalid model.parameters contract"):
        _validate_model_shape(payload)

    payload = model_payload()
    monkeypatch.setattr(experiment_module, "_MAX_PARAMETER_VALUES", 1)
    parameters = payload["parameters"]
    assert isinstance(parameters, list)
    assert isinstance(parameters[0], dict)
    parameters[0]["value_specification"] = {"kind": "empirical", "seconds": [1.0]}
    assert _validate_model_shape(payload) == payload
    parameters[0]["value_specification"] = {"kind": "empirical", "seconds": [1.0, 2.0]}
    with pytest.raises(ValueError, match="model parameter values exceed the resource limit"):
        _validate_model_shape(payload)


def test_load_model_enforces_utc_identity_and_hash_contract(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    write_model(path)
    source = load_model(path)
    payload = model_payload()
    assert source.content_hash == hashlib.sha256(_canonical(payload)).hexdigest()
    assert source.parameter_provenance == (("review_effort.human", "assumed"),)

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("[", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid model artifact"):
        load_model(invalid_json)

    offset = tmp_path / "offset.json"
    write_model(offset)
    offset_payload = model_payload()
    offset_payload["training_cutoff"] = "2026-09-01T01:00:00+01:00"
    offset.write_text(json.dumps(offset_payload), encoding="utf-8")
    with pytest.raises(ValueError, match="model training_cutoff must be an aware UTC datetime"):
        load_model(offset)

    duplicate = model_payload()
    parameters = duplicate["parameters"]
    assert isinstance(parameters, list)
    parameters.append(parameters[0])
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(ValueError, match="model parameter names must be unique"):
        load_model(duplicate_path)


def test_service_distribution_resolves_all_kinds_and_rejects_invalid_shapes() -> None:
    assert _service_distribution((effort_parameter({"kind": "constant", "seconds": 4.5}),)) == ServiceDistribution(
        "constant", (4.5,)
    )
    assert _service_distribution(
        (effort_parameter({"kind": "lognormal", "median_seconds": 4.5, "sigma": 0.25}),)
    ) == ServiceDistribution("lognormal", (4.5, 0.25))
    assert _service_distribution(
        (effort_parameter({"kind": "empirical", "seconds": [1, 2.5]}),)
    ) == ServiceDistribution("empirical", (1.0, 2.5))

    invalid: tuple[tuple[Parameter, ...], str] = ((effort_parameter({"kind": "constant", "seconds": True}),), "invalid")
    with pytest.raises(ValueError, match="model is missing review_effort.human"):
        _service_distribution(())
    with pytest.raises(ValueError, match="model review_effort.human has an invalid duration"):
        _service_distribution(invalid[0])
    with pytest.raises(ValueError, match="model review_effort.human has an invalid lognormal duration"):
        _service_distribution((effort_parameter({"kind": "lognormal", "median_seconds": True, "sigma": 0.2}),))
    with pytest.raises(ValueError, match="model review_effort.human has an invalid lognormal duration"):
        _service_distribution((effort_parameter({"kind": "lognormal", "median_seconds": 2, "sigma": False}),))
    with pytest.raises(ValueError, match="model review_effort.human has an invalid empirical duration"):
        _service_distribution((effort_parameter({"kind": "empirical", "seconds": []}),))
    with pytest.raises(ValueError, match="model review_effort.human has an invalid empirical duration"):
        _service_distribution((effort_parameter({"kind": "empirical", "seconds": [True]}),))
    with pytest.raises(ValueError, match="model review_effort.human has an unsupported duration distribution"):
        _service_distribution((effort_parameter({"kind": "other", "seconds": [1]}),))


def test_exact_keys_and_calendar_resolution_preserve_contracts() -> None:
    value = {"a": 1, "b": 2}
    assert _exact_keys(value, frozenset(("a", "b")), "value") == value
    with pytest.raises(ValueError, match="invalid value contract"):
        _exact_keys({"a": 1}, frozenset(("a", "b")), "value")
    with pytest.raises(ValueError, match="invalid value contract"):
        _exact_keys([], frozenset(("a", "b")), "value")

    absence = AbsenceConfig(start=datetime(2026, 9, 8, 1), end=datetime(2026, 9, 8, 2))
    config = calendar_config(absences=(absence,))
    resolved = _calendar(config)
    assert resolved == DutyCalendar(
        "UTC",
        (WeeklyWindow("morning", 1, time(1), time(2)),),
        (LocalAbsence(absence.start, absence.end),),
    )


def test_calendar_maps_and_reviewer_defaults_are_deterministic() -> None:
    duty = calendar_config()
    different_duty = calendar_config(
        windows=(WeeklyWindowConfig(name="evening", weekday=1, start=time(3), end=time(4)),)
    )
    execution = ExecutionConfig(
        calendars=(duty,),
        reviewers=(ReviewerConfig(name="alice", calendar="duty"),),
    )
    declared = ScenarioConfig(schema_version=1, execution=execution, scenarios=())
    assert tuple(_calendar_map(declared)) == ("duty",)
    assert _reviewer_calendars(declared, {"duty": _calendar(duty)}) == (("alice", "duty"),)

    fallback = ScenarioConfig(
        schema_version=1,
        scenarios=(ScenarioEntryConfig(name="load", calendars=(duty,)),),
    )
    assert tuple(_calendar_map(fallback)) == ("duty",)
    assert _reviewer_calendars(fallback, {"duty": _calendar(duty)}) == (("reviewer", "duty"),)

    absence = AbsenceConfig(start=datetime(2026, 9, 8, 1), end=datetime(2026, 9, 8, 2))
    with_absences = ScenarioConfig(
        schema_version=1,
        scenarios=(
            ScenarioEntryConfig(
                name="load",
                absences=(ReviewerAbsencesConfig(reviewer="bob", absences=(absence,)),),
            ),
            ScenarioEntryConfig(
                name="other",
                absences=(ReviewerAbsencesConfig(reviewer="alice", absences=(absence,)),),
            ),
        ),
    )
    assert _reviewer_calendars(with_absences, {"duty": _calendar(duty)}) == (
        ("alice", "duty"),
        ("bob", "duty"),
    )
    assert _reviewer_calendars(ScenarioConfig(schema_version=1, scenarios=()), {}) == ()
    with pytest.raises(ValueError, match="scenario absences require a declared reviewer calendar"):
        _reviewer_calendars(with_absences, {})

    conflicting = ScenarioConfig(
        schema_version=1,
        scenarios=(
            ScenarioEntryConfig(name="one", calendars=(duty,)),
            ScenarioEntryConfig(name="two", calendars=(different_duty,)),
        ),
    )
    with pytest.raises(ValueError, match="conflicting calendar definition: duty"):
        _calendar_map(conflicting)


def test_scenario_and_execution_resolution_preserve_demand_capacity_and_timezone() -> None:
    absence = AbsenceConfig(start=datetime(2026, 9, 8, 1), end=datetime(2026, 9, 8, 2))
    entry = ScenarioEntryConfig(
        name="replacement",
        demand=ReplacementDemandConfig(kind="replacement_ai", fraction=0.25),
        calendars=(calendar_config(),),
        absences=(ReviewerAbsencesConfig(reviewer="alice", absences=(absence,)),),
        bypass=ReviewBypassConfig(eligible_fraction=0.5, audit_fraction=0.2),
    )
    resolved = _scenario(entry)
    assert resolved.name == "replacement"
    assert resolved.demand == ReplacementAI(0.25)
    assert resolved.calendars == (("duty", _calendar(calendar_config())),)
    assert resolved.absences == (("alice", (LocalAbsence(absence.start, absence.end),)),)
    assert resolved.bypass == ReviewBypass(0.5, 0.2)
    additive = _scenario(
        ScenarioEntryConfig(name="additive", demand=AdditiveDemandConfig(kind="additive_ai", fraction=2))
    )
    assert additive.demand == AdditiveAI(2)

    explicit = ExecutionConfig(observation_start=datetime(2026, 9, 8), horizon_days=2)
    explicit_config = ScenarioConfig(schema_version=1, execution=explicit, scenarios=())
    assert _execution(model(), explicit_config) is explicit

    local_cutoff = replace(
        model(),
        timezone="America/New_York",
        training_cutoff=datetime(2026, 9, 1, 1, tzinfo=UTC),
    )
    fallback = _execution(local_cutoff, ScenarioConfig(schema_version=1, scenarios=()))
    assert fallback.observation_start == datetime(2026, 8, 31)
    with pytest.raises(ValueError, match="model has an invalid timezone"):
        _execution(replace(model(), timezone="not/a-zone"), ScenarioConfig(schema_version=1, scenarios=()))


def test_build_experiment_propagates_execution_and_rejects_undeclared_overrides() -> None:
    calendar = calendar_config()
    absence = AbsenceConfig(start=datetime(2026, 9, 8, 1), end=datetime(2026, 9, 8, 2))
    entry = ScenarioEntryConfig(
        name="replacement",
        demand=ReplacementDemandConfig(kind="replacement_ai", fraction=0.25),
        calendars=(calendar,),
        absences=(ReviewerAbsencesConfig(reviewer="alice", absences=(absence,)),),
        bypass=ReviewBypassConfig(eligible_fraction=0.5, audit_fraction=0.2),
    )
    execution = ExecutionConfig(
        observation_start=datetime(2026, 9, 8),
        horizon_days=2,
        warmup_days=1,
        root_seed=9,
        replications=2,
        trace_replications=(1,),
        fixed_horizon_seconds=99,
        backlog_threshold=3,
        calendars=(calendar,),
        reviewers=(ReviewerConfig(name="alice", calendar="duty"),),
    )
    source = ModelSource(model(), "c" * 64, (("review_effort.human", "assumed"),))
    experiment = build_experiment(source, ScenarioConfig(schema_version=1, execution=execution, scenarios=(entry,)))
    assert experiment.bounds.observation.seconds == 2 * 86_400
    assert experiment.bounds.warmup_seconds == 86_400
    assert experiment.root_seed == 9
    assert experiment.replications == 2
    assert experiment.trace_replications == (1,)
    assert experiment.fixed_horizon_seconds == 99
    assert experiment.backlog_threshold == 3
    assert experiment.reviewer_calendars == (("alice", "duty"),)
    assert experiment.assumptions[0].service_distribution == ServiceDistribution("constant", (10.0,))
    assert experiment.scenarios == (_scenario(entry),)

    with pytest.raises(ValueError, match="execution observation_start is required"):
        build_experiment(source, ScenarioConfig(schema_version=1, execution=ExecutionConfig(), scenarios=()))

    undeclared_calendar = ScenarioConfig(
        schema_version=1,
        execution=ExecutionConfig(observation_start=datetime(2026, 9, 8), calendars=(calendar,)),
        scenarios=(ScenarioEntryConfig(name="load", calendars=(calendar_config("other"),)),),
    )
    with pytest.raises(ValueError, match="scenario calendar override is not declared by execution"):
        build_experiment(source, undeclared_calendar)

    undeclared_reviewer = ScenarioConfig(
        schema_version=1,
        execution=ExecutionConfig(
            observation_start=datetime(2026, 9, 8),
            calendars=(calendar,),
            reviewers=(ReviewerConfig(name="alice", calendar="duty"),),
        ),
        scenarios=(
            ScenarioEntryConfig(
                name="load",
                absences=(ReviewerAbsencesConfig(reviewer="bob", absences=(absence,)),),
            ),
        ),
    )
    with pytest.raises(ValueError, match="scenario absence reviewer is not declared by execution"):
        build_experiment(source, undeclared_reviewer)


def test_validation_and_results_lineage_contracts_reject_incompatible_artifacts(tmp_path: Path) -> None:
    valid = validation("c" * 64)
    validation_path = tmp_path / "validation.json"
    validation_path.write_text(valid.model_dump_json(), encoding="utf-8")
    assert _validation(validation_path).status == "pass"

    invalid_schema = valid.model_dump(mode="json")
    invalid_schema["schema_version"] = True
    validation_path.write_text(json.dumps(invalid_schema), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported validation schema version"):
        _validation(validation_path)

    validation_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid validation artifact"):
        _validation(validation_path)

    results = tmp_path / "results"
    results.mkdir()
    manifest_path = results / "manifest.json"
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source_model_content_hash": "d" * 64,
        "source_model_version": "fifo-v0.1",
        "dataset_content_hash": "a" * 64,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _check_lineage(results, valid)

    manifest_path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid results manifest contract"):
        _check_lineage(results, valid)
    manifest_path.write_text(json.dumps({**manifest, "schema_version": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported results manifest schema version"):
        _check_lineage(results, valid)
    manifest_path.write_text(json.dumps({**manifest, "source_model_content_hash": "short"}), encoding="utf-8")
    with pytest.raises(ValueError, match="results manifest is missing model lineage"):
        _check_lineage(results, valid)
    manifest_path.write_text(json.dumps({**manifest, "dataset_content_hash": "g" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="results manifest is missing model lineage"):
        _check_lineage(results, valid)
    manifest_path.write_text(json.dumps({**manifest, "source_model_version": "other"}), encoding="utf-8")
    with pytest.raises(ValueError, match="validation and results lineage do not match"):
        _check_lineage(results, valid)
    manifest_path.write_text(json.dumps({**manifest, "dataset_content_hash": "b" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="validation and results lineage do not match"):
        _check_lineage(results, valid)

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for invalid_hash in ("", "g" * 64, "0" * 64):
        with pytest.raises(ValueError, match="validation artifact has an unbound model content hash"):
            _check_lineage(results, valid.model_copy(update={"model_content_hash": invalid_hash}))


def test_report_renders_saved_results_with_validation_and_atomic_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_path, scenarios_path, results = tmp_path / "model.json", tmp_path / "scenarios.yaml", tmp_path / "results"
    write_model(model_path)
    write_scenarios(scenarios_path)
    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            ["simulate", "--model", str(model_path), "--scenarios", str(scenarios_path), "--out", str(results)],
        ).exit_code
        == 0
    )
    manifest = json.loads((results / "manifest.json").read_text())
    validation_path = tmp_path / "validation.json"
    validation_path.write_text(validation(manifest["source_model_content_hash"]).model_dump_json(), encoding="utf-8")
    report = tmp_path / "report.md"

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("report must not execute simulation")

    monkeypatch.setattr("merge_carlo.simulation.runner.run_experiment", forbidden)
    written = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(report),
        ],
    )
    assert written.exit_code == 0, written.output
    assert "CONDITIONAL MODEL OUTPUT" in report.read_text()
    assert "Validation: pass" in report.read_text()
    combined_report = report.read_text()
    assert "## Fit diagnostics" in combined_report
    assert "Protocol: `held_out`" in combined_report
    assert "multiple required approvals" in combined_report
    assert "structural-fit limitations to investigate, not measured causes" in combined_report

    report.write_text("keep", encoding="utf-8")
    refused = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(report),
        ],
    )
    assert refused.exit_code == 2
    assert report.read_text() == "keep"
    replaced = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(report),
            "--overwrite",
        ],
    )
    assert replaced.exit_code == 0
    assert "Validation: pass" in report.read_text()

    in_bundle = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(results / "report.md"),
            "--overwrite",
        ],
    )
    assert in_bundle.exit_code == 0, in_bundle.output
    manifest = json.loads((results / "manifest.json").read_text())
    assert manifest["content_hashes"]["report.md"] == hashlib.sha256((results / "report.md").read_bytes()).hexdigest()
    assert manifest["validation_status"] == "pass"


def test_report_rejects_an_unbound_validation_model_hash(tmp_path: Path) -> None:
    model_path, scenarios_path, results = tmp_path / "model.json", tmp_path / "scenarios.yaml", tmp_path / "results"
    write_model(model_path)
    write_scenarios(scenarios_path)
    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            ["simulate", "--model", str(model_path), "--scenarios", str(scenarios_path), "--out", str(results)],
        ).exit_code
        == 0
    )
    manifest = json.loads((results / "manifest.json").read_text())
    validation_path = tmp_path / "validation.json"
    invalid_schema = validation("e" * 64).model_dump(mode="json")
    invalid_schema["schema_version"] = True
    validation_path.write_text(json.dumps(invalid_schema), encoding="utf-8")
    report = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(tmp_path / "invalid-schema.md"),
        ],
    )
    assert report.exit_code == 2

    validation_path.write_text(validation("0" * 64).model_dump_json(), encoding="utf-8")
    report = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(validation_path),
            "--out",
            str(tmp_path / "report.md"),
        ],
    )
    assert report.exit_code == 2
    assert "unbound" in report.output.lower()

    mismatched = tmp_path / "mismatched.json"
    mismatched.write_text(validation("e" * 64).model_dump_json(), encoding="utf-8")
    report = runner.invoke(
        app,
        [
            "report",
            "--results",
            str(results),
            "--validation",
            str(mismatched),
            "--out",
            str(tmp_path / "mismatched.md"),
        ],
    )
    assert report.exit_code == 0, report.output
    assert manifest["source_model_content_hash"] != "e" * 64


def test_write_report_does_not_clobber_after_a_concurrent_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "report.md"

    def concurrent_create(*args: object, **kwargs: object) -> None:
        Path(str(args[1])).write_text("keep", encoding="utf-8")
        raise FileExistsError

    monkeypatch.setattr("merge_carlo.reporting.os.link", concurrent_create)
    with pytest.raises(FileExistsError):
        write_report("replace", out)
    assert out.read_text() == "keep"
