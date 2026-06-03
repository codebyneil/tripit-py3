"""Shared pytest fixtures + skip-by-default wiring for @pytest.mark.live."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
XML_DIR = FIXTURES_DIR / "xml"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def load_xml_fixture() -> Callable[[str], bytes]:
    def _load(name: str) -> bytes:
        return (XML_DIR / name).read_bytes()

    return _load


def load_xml(name: str) -> bytes:
    """Module-level XML fixture loader for use outside fixtures."""
    return (XML_DIR / name).read_bytes()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip @pytest.mark.live tests unless `-m live` (or stronger) is passed."""
    mark_expr = config.getoption("-m") or ""
    if "live" in mark_expr:
        return  # user explicitly opted in
    skip_live = pytest.mark.skip(
        reason="live API test; run with `pytest -m live` and TRIPIT_* env vars set."
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
