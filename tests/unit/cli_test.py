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
