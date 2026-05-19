"""End-to-end tests for the Phase 2 read methods."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from tripit import TripIt
from tripit.exceptions import TripItNotFoundError

FIXTURES = Path(__file__).parent / "fixtures" / "json"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _client() -> TripIt:
    return TripIt(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        token_secret="ts",
        api_url="https://api.tripit.example",
    )


@respx.mock
def test_get_profile() -> None:
    respx.get("https://api.tripit.example/v1/get/profile").mock(
        return_value=httpx.Response(200, json=_load("get_profile.json"))
    )
    with _client() as c:
        profile = c.get_profile()
    assert profile.screen_name == "neilauto"
    assert profile.home_airport == "YYZ"


@respx.mock
def test_get_profile_missing_raises_not_found() -> None:
    empty = {"Response": {"timestamp": 1, "num_bytes": 1}}
    respx.get("https://api.tripit.example/v1/get/profile").mock(
        return_value=httpx.Response(200, json=empty)
    )
    with _client() as c, pytest.raises(TripItNotFoundError):
        c.get_profile()


@respx.mock
def test_get_air_returns_typed_air_object() -> None:
    respx.get("https://api.tripit.example/v1/get/air").mock(
        return_value=httpx.Response(200, json=_load("get_air.json"))
    )
    with _client() as c:
        air = c.get_air("555111")
    assert air.id == "555111"
    assert air.supplier_name == "Air Canada"
    assert len(air.segments) == 1


@respx.mock
def test_list_points_programs_returns_list() -> None:
    respx.get("https://api.tripit.example/v1/list/points_program").mock(
        return_value=httpx.Response(200, json=_load("list_points_program.json"))
    )
    with _client() as c:
        programs = c.list_points_programs()
    assert [p.name for p in programs] == ["Aeroplan", "Marriott Bonvoy"]


@respx.mock
def test_get_points_program_single() -> None:
    single = {"Response": {"PointsProgram": {"id": "111", "name": "Aeroplan", "balance": "85000"}}}
    respx.get("https://api.tripit.example/v1/get/points_program").mock(
        return_value=httpx.Response(200, json=single)
    )
    with _client() as c:
        prog = c.get_points_program("111")
    assert prog.name == "Aeroplan"


@respx.mock
def test_list_objects_envelope_iterates_pages() -> None:
    p1 = {
        "Response": {
            "page_num": 1,
            "page_size": 25,
            "max_page": 2,
            "AirObject": {"id": "1", "display_name": "AC 23"},
            "LodgingObject": [{"id": "2", "supplier_name": "Hilton"}],
        }
    }
    p2 = {
        "Response": {
            "page_num": 2,
            "page_size": 25,
            "max_page": 2,
            "CarObject": {"id": "3", "supplier_name": "Hertz"},
        }
    }
    route = respx.get("https://api.tripit.example/v1/list/object")
    route.side_effect = [
        httpx.Response(200, json=p1),
        httpx.Response(200, json=p2),
    ]
    with _client() as c:
        envelopes = list(c.list_objects_envelope(trip_id="999"))
    assert len(envelopes) == 2
    assert envelopes[0].air_objects[0].display_name == "AC 23"
    assert envelopes[0].lodging_objects[0].supplier_name == "Hilton"
    assert envelopes[1].car_objects[0].supplier_name == "Hertz"
