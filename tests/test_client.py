"""End-to-end tests for the high-level TripIt client (reads only in Phase 1)."""

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
def test_list_trips_paginates_transparently() -> None:
    payload = _load("list_trip_single_page.json")
    page2 = {
        "Response": {
            "page_num": 2,
            "page_size": 25,
            "max_page": 2,
            "Trip": [{"id": "777", "display_name": "Late add"}],
        }
    }
    # Page 1 says max_page=2 by overriding the fixture's max_page.
    page1 = json.loads(json.dumps(payload))
    page1["Response"]["max_page"] = 2

    route = respx.get("https://api.tripit.example/v1/list/trip")
    route.side_effect = [
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ]
    with _client() as c:
        trips = list(c.list_trips())
    assert [t.id for t in trips] == ["999000111222", "999000111223", "777"]
    assert route.call_count == 2


@respx.mock
def test_list_trips_filters_pass_through_as_query_params() -> None:
    route = respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, json=_load("list_trip_single_page.json"))
    )
    with _client() as c:
        list(c.list_trips(past=True, traveler="only", modified_since=1700000000))
    params = route.calls.last.request.url.params
    assert params["past"] == "true"
    assert params["traveler"] == "only"
    assert params["modified_since"] == "1700000000"


@respx.mock
def test_get_trip_returns_typed_trip() -> None:
    respx.get("https://api.tripit.example/v1/get/trip/id/999000111222").mock(
        return_value=httpx.Response(200, json=_load("get_trip_single.json"))
    )
    with _client() as c:
        trip = c.get_trip("999000111222")
    assert trip.id == "999000111222"
    assert trip.display_name == "Tokyo Vacation"


@respx.mock
def test_get_trip_uses_path_form_id() -> None:
    route = respx.get("https://api.tripit.example/v1/get/trip/id/999000111222").mock(
        return_value=httpx.Response(200, json=_load("get_trip_single.json"))
    )
    with _client() as c:
        c.get_trip("999000111222")
    assert route.called
    # Verify the id is in the URL path, not as a query param.
    assert "id=" not in str(route.calls.last.request.url.query)


@respx.mock
def test_get_trip_with_no_results_raises_not_found() -> None:
    empty = {"Response": {"timestamp": 1, "num_bytes": 1}}
    respx.get("https://api.tripit.example/v1/get/trip/id/nonexistent").mock(
        return_value=httpx.Response(200, json=empty)
    )
    with _client() as c, pytest.raises(TripItNotFoundError):
        c.get_trip("nonexistent")
