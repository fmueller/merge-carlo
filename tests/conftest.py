"""Shared test helpers."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """A Typer CLI runner for exercising the command surface."""
    return CliRunner()
