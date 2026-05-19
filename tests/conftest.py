"""Shared pytest fixtures + skip-by-default wiring for @pytest.mark.live."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def load_json_fixture() -> object:
    def _load(name: str) -> object:
        path = FIXTURES_DIR / "json" / name
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    return _load


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip @pytest.mark.live tests unless `-m live` (or stronger) is passed.

    The default `pytest` invocation must never hit the real TripIt API. The
    live test is opt-in: `uv run pytest -m live tests/test_oauth_live.py`.
    """
    mark_expr = config.getoption("-m") or ""
    if "live" in mark_expr:
        return  # user explicitly opted in
    skip_live = pytest.mark.skip(
        reason="live API test; run with `pytest -m live` and TRIPIT_* env vars set."
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
