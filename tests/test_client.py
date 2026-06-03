"""End-to-end tests for the high-level TripIt client (trip reads)."""

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


_PAGE2 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Response><timestamp>1</timestamp><num_bytes>1</num_bytes>
<Trip><id>777</id><display_name>Late add</display_name></Trip>
<page_num>2</page_num><page_size>25</page_size><max_page>2</max_page></Response>"""


@respx.mock
def test_list_trips_paginates_transparently() -> None:
    page1 = _load("list_trip_single_page.xml").replace(
        b"<max_page>1</max_page>", b"<max_page>2</max_page>"
    )
    route = respx.get("https://api.tripit.example/v1/list/trip")
    route.side_effect = [
        httpx.Response(200, content=page1),
        httpx.Response(200, content=_PAGE2),
    ]
    with _client() as c:
        trips = list(c.list_trips())
    assert [t.id for t in trips] == ["111", "222", "777"]
    assert route.call_count == 2


@respx.mock
def test_list_trips_filters_pass_through_as_query_params() -> None:
    route = respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, content=_load("list_trip_single_page.xml"))
    )
    with _client() as c:
        list(c.list_trips(past=True, traveler="only", modified_since=1700000000))
    params = route.calls.last.request.url.params
    assert params["past"] == "true"
    assert params["traveler"] == "only"
    assert params["modified_since"] == "1700000000"


@respx.mock
def test_get_trip_returns_typed_trip() -> None:
    respx.get("https://api.tripit.example/v1/get/trip/id/111").mock(
        return_value=httpx.Response(200, content=_load("get_trip_single.xml"))
    )
    with _client() as c:
        trip = c.get_trip("111")
    assert trip.id == "111"
    assert trip.display_name == "Seattle to New York"


@respx.mock
def test_get_trip_uses_path_form_id() -> None:
    route = respx.get("https://api.tripit.example/v1/get/trip/id/111").mock(
        return_value=httpx.Response(200, content=_load("get_trip_single.xml"))
    )
    with _client() as c:
        c.get_trip("111")
    assert route.called
    assert "id=" not in str(route.calls.last.request.url.query)


@respx.mock
def test_get_trip_with_no_results_raises_not_found() -> None:
    empty = b'<Response><timestamp>1</timestamp><num_bytes>1</num_bytes></Response>'
    respx.get("https://api.tripit.example/v1/get/trip/id/nonexistent").mock(
        return_value=httpx.Response(200, content=empty)
    )
    with _client() as c, pytest.raises(TripItNotFoundError):
        c.get_trip("nonexistent")
