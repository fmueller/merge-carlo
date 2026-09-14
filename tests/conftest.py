"""Shared test helpers."""

import os
import time
from collections.abc import Callable, Iterator

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """A Typer CLI runner for exercising the command surface."""
    return CliRunner()


@pytest.fixture
def pin_host_timezone(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str], None]]:
    """Pin the process timezone for tests that must not inherit the host zone."""
    previous = os.environ.get("TZ")

    def pin(name: str) -> None:
        monkeypatch.setenv("TZ", name)
        time.tzset()

    yield pin
    if previous is None:
        monkeypatch.delenv("TZ", raising=False)
    else:
        monkeypatch.setenv("TZ", previous)
    time.tzset()
