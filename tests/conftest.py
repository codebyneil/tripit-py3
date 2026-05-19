"""Shared pytest fixtures."""

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
