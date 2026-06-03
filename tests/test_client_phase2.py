"""End-to-end tests for profile / points / object read methods."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tripit import TripIt
from tripit.exceptions import TripItNotFoundError

XML = Path(__file__).parent / "fixtures" / "xml"


def _load(name: str) -> bytes:
    return (XML / name).read_bytes()


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
        return_value=httpx.Response(200, content=_load("get_profile.xml"))
    )
    with _client() as c:
        prof = c.get_profile()
    assert prof.screen_name == "neiltraveler"
    assert prof.home_airport == "SEA"


@respx.mock
def test_get_profile_missing_raises_not_found() -> None:
    empty = b"<Response><timestamp>1</timestamp><num_bytes>1</num_bytes></Response>"
    respx.get("https://api.tripit.example/v1/get/profile").mock(
        return_value=httpx.Response(200, content=empty)
    )
    with _client() as c, pytest.raises(TripItNotFoundError):
        c.get_profile()


@respx.mock
def test_get_air_returns_typed_air_object() -> None:
    respx.get("https://api.tripit.example/v1/get/air/id/900100").mock(
        return_value=httpx.Response(200, content=_load("get_air.xml"))
    )
    with _client() as c:
        air = c.get_air("900100")
    assert air.id == "900100"
    assert air.segments[0].start_airport_code == "SEA"


@respx.mock
def test_list_points_programs_returns_list() -> None:
    respx.get("https://api.tripit.example/v1/list/points_program").mock(
        return_value=httpx.Response(200, content=_load("list_points_program.xml"))
    )
    with _client() as c:
        programs = c.list_points_programs()
    assert [p.name for p in programs] == ["Alaska Mileage Plan", "Marriott Bonvoy"]


@respx.mock
def test_get_points_program_single() -> None:
    respx.get("https://api.tripit.example/v1/get/points_program/id/5001").mock(
        return_value=httpx.Response(200, content=_load("list_points_program.xml"))
    )
    with _client() as c:
        program = c.get_points_program("5001")
    assert program.id == "5001"


@respx.mock
def test_list_objects_envelope_yields_mixed_types() -> None:
    respx.get("https://api.tripit.example/v1/list/object").mock(
        return_value=httpx.Response(200, content=_load("list_object_mixed.xml"))
    )
    with _client() as c:
        pages = list(c.list_objects_envelope(type="all"))
    assert len(pages) == 1
    env = pages[0]
    assert len(env.air_objects) == 1
    assert len(env.lodging_objects) == 1
    assert len(env.car_objects) == 1
