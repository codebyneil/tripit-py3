"""End-to-end tests for Phase 3 write methods."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import respx
from lxml import etree

from tripit import Trip, TripIt
from tripit.models.objects import NoteObject

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


def _form_field(body: bytes, field: str) -> str:
    from urllib.parse import parse_qs

    parsed = parse_qs(body.decode("utf-8"))
    return parsed[field][0]


@respx.mock
def test_create_trip_posts_xml_and_returns_typed_response() -> None:
    response_payload = _load("get_trip_single.json")
    route = respx.post("https://api.tripit.example/v1/create").mock(
        return_value=httpx.Response(200, json=response_payload)
    )
    trip_to_create = Trip(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        display_name="New trip",
        primary_location="Tokyo, JP",
    )
    with _client() as c:
        created = c.create_trip(trip_to_create)
    assert created.id == "999000111222"

    # Verify the request body carried valid XML in the `xml` form field.
    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    xml_str = _form_field(req.content, "xml")
    root = etree.fromstring(xml_str.encode("utf-8"))
    assert root.tag == "Request"
    inner = root.find("Trip")
    assert inner is not None
    assert inner.findtext("display_name") == "New trip"


@respx.mock
def test_replace_trip_posts_id_and_xml() -> None:
    response_payload = _load("get_trip_single.json")
    route = respx.post("https://api.tripit.example/v1/replace/trip").mock(
        return_value=httpx.Response(200, json=response_payload)
    )
    with _client() as c:
        c.replace_trip("999000111222", Trip(display_name="Renamed"))

    req = route.calls.last.request
    assert _form_field(req.content, "id") == "999000111222"
    xml_str = _form_field(req.content, "xml")
    root = etree.fromstring(xml_str.encode("utf-8"))
    assert root.find("Trip/display_name").text == "Renamed"


@respx.mock
def test_delete_trip_posts_id_only_returns_none() -> None:
    empty = {"Response": {"timestamp": 1, "num_bytes": 1}}
    route = respx.post("https://api.tripit.example/v1/delete/trip").mock(
        return_value=httpx.Response(200, json=empty)
    )
    with _client() as c:
        result = c.delete_trip("999000111222")
    assert result is None
    req = route.calls.last.request
    assert _form_field(req.content, "id") == "999000111222"
    # No xml field on delete.
    from urllib.parse import parse_qs

    assert "xml" not in parse_qs(req.content.decode("utf-8"))


@respx.mock
def test_create_note_serializes_note_object_payload() -> None:
    response_payload = {
        "Response": {"NoteObject": {"id": "777", "display_name": "memo", "text": "hi"}}
    }
    route = respx.post("https://api.tripit.example/v1/create").mock(
        return_value=httpx.Response(200, json=response_payload)
    )
    with _client() as c:
        created = c.create_note(NoteObject(display_name="memo", text="hi"))
    assert created.id == "777"
    req = route.calls.last.request
    xml_str = _form_field(req.content, "xml")
    root = etree.fromstring(xml_str.encode("utf-8"))
    assert root.find("NoteObject/display_name").text == "memo"
    assert root.find("NoteObject/text").text == "hi"


@respx.mock
def test_crs_delete_reservations_posts_record_locator() -> None:
    empty = {"Response": {"timestamp": 1, "num_bytes": 1}}
    route = respx.post("https://api.tripit.example/v1/crsDeleteReservations").mock(
        return_value=httpx.Response(200, json=empty)
    )
    with _client() as c:
        c.crs_delete_reservations("LOC-ABC-123")
    req = route.calls.last.request
    assert _form_field(req.content, "record_locator") == "LOC-ABC-123"


@respx.mock
def test_crs_load_reservations_passes_xml_and_company_key() -> None:
    response_payload = {"Response": {"timestamp": 1, "num_bytes": 1, "Trip": []}}
    route = respx.post("https://api.tripit.example/v1/crsLoadReservations").mock(
        return_value=httpx.Response(200, json=response_payload)
    )
    payload = "<Request><Trip><display_name>x</display_name></Trip></Request>"
    with _client() as c:
        envelope = c.crs_load_reservations(payload, company_key="ck-99")
    assert envelope.trips == []
    req = route.calls.last.request
    assert _form_field(req.content, "company_key") == "ck-99"
    assert _form_field(req.content, "xml") == payload
