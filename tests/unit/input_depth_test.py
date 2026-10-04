"""Parser depth failures are invalid input, not internal CLI errors."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from merge_carlo.cli import app
from merge_carlo.configuration import load_assumption_config, load_scenario_config
from merge_carlo.experiment import load_model
from merge_carlo.validation import load_validation_evidence
from tests.unit.experiment_test import write_model, write_scenarios

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("kind", ["assumptions", "scenarios", "model", "validation"])
def test_loaders_reject_parser_depth_failures(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "deep"
    if kind in {"assumptions", "scenarios"}:
        source.write_text("schema_version: 1\nscenarios: " + "[" * 2000 + "0" + "]" * 2000)
        assert source.stat().st_size < 1024 * 1024
        loader = load_assumption_config if kind == "assumptions" else load_scenario_config
        with pytest.raises(ValueError, match="^invalid configuration$"):
            loader(source)
    else:
        source.write_text("[" * 20000 + "0" + "]" * 20000)
        assert source.stat().st_size < 16 * 1024 * 1024
        with pytest.raises(
            ValueError, match=f"^invalid {'model artifact' if kind == 'model' else 'validation evidence'}$"
        ):
            if kind == "model":
                load_model(source)
            else:
                load_validation_evidence(source)


@pytest.mark.parametrize("kind", ["scenarios", "model", "validation"])
@pytest.mark.parametrize("machine", [False, True])
def test_cli_rejects_parser_depth_without_bundle(tmp_path: Path, kind: str, machine: bool) -> None:
    model = tmp_path / "model.json"
    scenarios = tmp_path / "scenarios.yaml"
    write_model(model)
    write_scenarios(scenarios)
    source = tmp_path / "deep"
    out = tmp_path / "out"
    if kind == "scenarios":
        source.write_text("schema_version: 1\nscenarios: " + "[" * 2000 + "0" + "]" * 2000)
    else:
        source.write_text("[" * 20000 + "0" + "]" * 20000)
    if kind == "validation":
        args = ["validate", "--input", str(source), "--out", str(out)]
        message = "Cannot validate: invalid or inaccessible evidence/output."
    else:
        args = [
            "simulate",
            "--model",
            str(source if kind == "model" else model),
            "--scenarios",
            str(source if kind == "scenarios" else scenarios),
            "--out",
            str(out),
        ]
        message = f"Cannot simulate: invalid {'configuration' if kind == 'scenarios' else 'model artifact'}"
    result = CliRunner().invoke(app, (["--json"] if machine else []) + args)
    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert not out.exists()
    if machine:
        assert json.loads(result.stdout) == {"exit_code": 2, "message": message, "status": "error"}
        assert not result.stderr
    else:
        assert result.stderr.strip() == message
