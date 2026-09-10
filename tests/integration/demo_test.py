"""The demo runs the real model without credentials, HTTP clients or sockets."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from merge_carlo.cli import app
from merge_carlo.reporting import render_report

pytestmark = pytest.mark.integration


def test_offline_demo_reproduces_complete_synthetic_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("demo must not construct a network client or socket")

    for token in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(token, raising=False)
    monkeypatch.setattr("httpx.Client", forbidden)
    monkeypatch.setattr("httpx.AsyncClient", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    outputs = []
    for name in ("first", "second"):
        out = tmp_path / name
        result = CliRunner().invoke(app, ["demo", "--out", str(out), "--seed", "42", "--replications", "2"])
        assert result.exit_code == 0, result.output
        assert "SYNTHETIC" in result.output
        assert "base assumption set" in result.output
        outputs.append({p.name: p.read_bytes() for p in out.iterdir()})
        manifest = json.loads((out / "manifest.json").read_text())
        assert manifest["synthetic"] is True
        assert manifest["root_seed"] == 42
        assert manifest["training_cutoff"] is None
        resolved = json.loads((out / "resolved-scenarios.json").read_text())
        assert resolved["synthetic"] is True
        config = resolved["experiment"]
        assert config["replications"] == 2
        assert [a["name"] for a in config["assumptions"]] == ["base"]
        assert len(config["templates"]) >= 2
        assert all(t["arrivals"] for t in config["templates"])
        assert {s["name"] for s in config["scenarios"]} == {
            "additive-ai",
            "replacement-ai",
            "extended-duty",
            "reviewer-absence",
            "hypothetical-bypass",
        }
        summary = json.loads((out / "summary.json").read_text())
        assert not summary["comparison_incomplete"]
        assert {r["scenario"] for r in summary["rows"]} == {
            "baseline",
            "additive-ai",
            "replacement-ai",
            "extended-duty",
            "reviewer-absence",
            "hypothetical-bypass",
        }
        assert all(r["summary"]["total"] == 2 for r in summary["rows"])
        assert any(r["summary"]["median"]["value"] > 0 for r in summary["rows"] if r["metric"] == "all_work.merges")
        for section in (out / "report.md").read_text().split("\n\n## "):
            assert "SYNTHETIC" in section
            assert "Only the base assumption set was run. Full sensitivity has not been run." in section
        assert render_report(out) == (out / "report.md").read_text()
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize("args", [["--seed", "-1"], ["--replications", "0"], ["--replications", "-2"]])
def test_invalid_demo_options_do_not_write(tmp_path: Path, args: list[str]) -> None:
    out = tmp_path / "out"
    result = CliRunner().invoke(app, ["demo", "--out", str(out), *args])
    assert result.exit_code == 2
    assert not out.exists()


def test_demo_preserves_existing_output(tmp_path: Path) -> None:
    (tmp_path / "precious").write_text("keep")
    result = CliRunner().invoke(app, ["demo", "--out", str(tmp_path), "--replications", "1"])
    assert result.exit_code == 2
    assert "nonempty output directory" in result.output
    assert {p.name: p.read_text() for p in tmp_path.iterdir()} == {"precious": "keep"}
