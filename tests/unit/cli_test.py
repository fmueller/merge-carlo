from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from merge_carlo import __version__
from merge_carlo.cli import app


@pytest.mark.unit
def test_version_option_prints_the_package_version(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


@pytest.mark.unit
def test_help_describes_the_tool(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "review capacity" in result.stdout


@pytest.mark.unit
def test_bare_invocation_reports_invalid_input(runner: CliRunner) -> None:
    # Exit code 2 is the documented "invalid input" code; a bare invocation
    # prints usage rather than doing anything.
    result = runner.invoke(app, [])

    assert result.exit_code == 2


@pytest.mark.unit
def test_collect_cli_and_resume(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 91} if request.url.path == "/repos/example/repo" else [])

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    args = [
        "collect",
        "--repo",
        "example/repo",
        "--start",
        "2026-01-01T00:00:00Z",
        "--end",
        "2026-02-01T00:00:00Z",
        "--out",
        str(tmp_path / "out"),
        "--workspace",
        str(tmp_path / "private"),
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    assert "complete" in first.stdout
    assert (tmp_path / "out" / "dataset.sqlite").is_file()
    assert runner.invoke(app, args).exit_code == 2
    assert runner.invoke(app, [*args, "--resume"]).exit_code == 0
    (tmp_path / "out" / "unrelated").write_text("KEEP")
    assert runner.invoke(app, [*args, "--resume"]).exit_code == 2
    assert (tmp_path / "out" / "unrelated").read_text() == "KEEP"


@pytest.mark.unit
@pytest.mark.parametrize("fail_identity", [True, False])
def test_collect_source_failures_exit_three(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_identity: bool
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if not fail_identity and request.url.path == "/repos/example/repo":
            return httpx.Response(200, json={"id": 91})
        return httpx.Response(403)

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    result = runner.invoke(
        app,
        [
            "collect",
            "--repo",
            "example/repo",
            "--start",
            "2026-01-01T00:00:00Z",
            "--end",
            "2026-02-01T00:00:00Z",
            "--out",
            str(tmp_path / "out"),
            "--workspace",
            str(tmp_path / "private"),
        ],
    )
    assert result.exit_code == 3


@pytest.mark.unit
@pytest.mark.parametrize("failure", ["identity", "malformed", "invalid_repo", "interrupt"])
def test_collect_can_retry_after_pre_manifest_failure(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    failed = True

    def respond(request: httpx.Request) -> httpx.Response:
        if failed:
            if failure == "interrupt":
                raise KeyboardInterrupt
            return httpx.Response(403) if failure == "identity" else httpx.Response(200, json={"id": "PRIVATE"})
        return httpx.Response(200, json={"id": 91} if request.url.path == "/repos/example/repo" else [])

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(respond))
    args = [
        "collect",
        "--repo",
        "bad/path?PRIVATE" if failure == "invalid_repo" else "example/repo",
        "--start",
        "2026-01-01T00:00:00Z",
        "--end",
        "2026-02-01T00:00:00Z",
        "--out",
        str(tmp_path / "out"),
        "--workspace",
        str(tmp_path / "private"),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert "PRIVATE" not in result.output
    assert not (tmp_path / "out" / "dataset.sqlite").exists()
    failed = False
    args[2] = "example/repo"
    assert runner.invoke(app, args).exit_code == 0
