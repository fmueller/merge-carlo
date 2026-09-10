"""Versioned, data-only configuration contracts and schema export."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from merge_carlo.configuration import (
    active_service_seconds,
    export_schemas,
    load_assumption_config,
    load_scenario_config,
)
from merge_carlo.simulation.calendars import LocalAbsence

pytestmark = pytest.mark.unit


def test_shipped_examples_validate_against_exported_schemas(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    examples = Path("examples")

    for name in ("assumptions", "scenarios"):
        schema = json.loads((tmp_path / f"{name}.schema.json").read_text(encoding="utf-8"))
        document = yaml.safe_load((examples / f"{name}.yaml").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(document)

    load_assumption_config(examples / "assumptions.yaml")
    load_scenario_config(examples / "scenarios.yaml")


def test_export_is_deterministic_and_documents_effort_composition(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"

    export_schemas(first)
    export_schemas(second)

    assert (first / "assumptions.schema.json").read_bytes() == (second / "assumptions.schema.json").read_bytes()
    assert {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in first.iterdir()} == {
        "assumptions.schema.json": "95efb5f78573385b50d7238277f130231e95701349a792391b3b4d696b7d5523",
        "scenarios.schema.json": "fd3cc02baa579fd8e17ef88a7bbd7aba5793bdf9e058d386e52f73de783a3dc5",
    }
    schema = json.loads((first / "assumptions.schema.json").read_text(encoding="utf-8"))
    multiplier = schema["$defs"]["AssumptionSetConfig"]["properties"]["effort_multiplier"]
    assert "ceil(sampled active-service seconds × effort_multiplier)" in multiplier["description"]
    assert "minimum of one second" in multiplier["description"]


def test_exported_schema_rejects_nonpositive_empirical_service(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    schema = json.loads((tmp_path / "assumptions.schema.json").read_text(encoding="utf-8"))
    document = yaml.safe_load(Path("examples/assumptions.yaml").read_text(encoding="utf-8"))
    document["assumptions"][0]["active_service"] = {"kind": "empirical", "seconds": [10, 0]}

    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(document)


@pytest.mark.parametrize(("sample", "multiplier", "expected"), [(0.01, 1.0, 1), (1.01, 1.0, 2), (2.0, 1.25, 3)])
def test_active_service_composes_multiplier_then_rounds_up(sample: float, multiplier: float, expected: int) -> None:
    assert active_service_seconds(sample, multiplier) == expected


@pytest.mark.parametrize(
    ("sample", "multiplier"),
    [(0.0, 1.0), (-1.0, 1.0), (1.0, 0.0), (1.0, -1.0), (True, 1.0), (1.0, True), (float("inf"), 1.0)],
)
def test_active_service_rejects_nonpositive_nonfinite_and_boolean_values(sample: float, multiplier: float) -> None:
    with pytest.raises(ValueError, match="active service and multiplier must be finite and positive"):
        active_service_seconds(sample, multiplier)


@pytest.mark.parametrize("loader", [load_assumption_config, load_scenario_config])
def test_configuration_rejects_unknown_keys_and_unsafe_yaml(loader: object, tmp_path: Path) -> None:
    assert callable(loader)
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text("schema_version: 1\nunknown: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid configuration"):
        loader(unknown)

    marker = tmp_path / "executed"
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text(f"!!python/object/apply:os.system ['touch {marker}']\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid configuration"):
        loader(unsafe)
    assert not marker.exists()


def test_calendar_times_reject_offsets_and_absences_normalize_fixed_offsets(tmp_path: Path) -> None:
    path = tmp_path / "scenarios.yaml"
    path.write_text(
        """schema_version: 1
scenarios:
  - name: capacity
    calendars:
      - name: duty
        timezone: Europe/Berlin
        windows:
          - name: morning
            weekday: 0
            start: 09:00:00+02:00
            end: 12:00:00
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid configuration"):
        load_scenario_config(path)

    path.write_text(
        """schema_version: 1
scenarios:
  - name: absent
    absences:
      - reviewer: reviewer-1
        absences:
          - start: 2026-01-01T09:00:00+02:00
            end: 2026-01-01T10:00:00+02:00
""",
        encoding="utf-8",
    )
    interval = load_scenario_config(path).scenarios[0].absences[0].absences[0]

    LocalAbsence(interval.start, interval.end)


def test_export_refuses_nonempty_output_without_changing_it(tmp_path: Path) -> None:
    out = tmp_path / "schemas"
    out.mkdir()
    existing = out / "keep.txt"
    existing.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="output directory must be empty or absent"):
        export_schemas(out)

    assert existing.read_text(encoding="utf-8") == "keep"


def test_export_creates_missing_parent_directories(tmp_path: Path) -> None:
    out = tmp_path / "missing" / "nested" / "schemas"

    export_schemas(out)

    assert (out / "assumptions.schema.json").is_file()
