"""End-to-end tests for write methods (create / replace / delete / CRS)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import respx
from lxml import etree

from tripit import Trip, TripIt
from tripit.models.objects import NoteObject

XML = Path(__file__).parent / "fixtures" / "xml"
_EMPTY = b"<Response><timestamp>1</timestamp><num_bytes>1</num_bytes></Response>"


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


def _form_field(body: bytes, field: str) -> str:
    return parse_qs(body.decode("utf-8"))[field][0]


@respx.mock
def test_create_trip_posts_xml_and_returns_typed_response() -> None:
    route = respx.post("https://api.tripit.example/v1/create").mock(
        return_value=httpx.Response(200, content=_load("get_trip_single.xml"))
    )
    trip_to_create = Trip(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        display_name="New trip",
        primary_location="Tokyo, JP",
    )
    with _client() as c:
        created = c.create_trip(trip_to_create)
    assert created.id == "111"

    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    root = etree.fromstring(_form_field(req.content, "xml").encode("utf-8"))
    assert root.tag == "Request"
    assert root.find("Trip").findtext("display_name") == "New trip"


@respx.mock
def test_replace_trip_uses_path_id_and_posts_xml() -> None:
    route = respx.post("https://api.tripit.example/v1/replace/trip/id/111").mock(
        return_value=httpx.Response(200, content=_load("get_trip_single.xml"))
    )
    with _client() as c:
        c.replace_trip("111", Trip(display_name="Renamed"))

    req = route.calls.last.request
    root = etree.fromstring(_form_field(req.content, "xml").encode("utf-8"))
    assert root.find("Trip/display_name").text == "Renamed"
    assert "id" not in parse_qs(req.content.decode("utf-8"))


@respx.mock
def test_delete_trip_uses_get_with_path_id() -> None:
    route = respx.get("https://api.tripit.example/v1/delete/trip/id/111").mock(
        return_value=httpx.Response(200, content=_EMPTY)
    )
    with _client() as c:
        result = c.delete_trip("111")
    assert result is None
    assert route.called


@respx.mock
def test_create_note_serializes_note_object_payload() -> None:
    resp = (
        b"<Response><timestamp>1</timestamp><num_bytes>1</num_bytes>"
        b"<NoteObject><id>777</id><display_name>memo</display_name><text>hi</text></NoteObject>"
        b"</Response>"
    )
    route = respx.post("https://api.tripit.example/v1/create").mock(
        return_value=httpx.Response(200, content=resp)
    )
    with _client() as c:
        created = c.create_note(NoteObject(display_name="memo", text="hi"))
    assert created.id == "777"
    root = etree.fromstring(_form_field(route.calls.last.request.content, "xml").encode("utf-8"))
    assert root.find("NoteObject/display_name").text == "memo"
    assert root.find("NoteObject/text").text == "hi"


@respx.mock
def test_crs_delete_reservations_posts_record_locator() -> None:
    route = respx.post("https://api.tripit.example/v1/crsDeleteReservations").mock(
        return_value=httpx.Response(200, content=_EMPTY)
    )
    with _client() as c:
        c.crs_delete_reservations("LOC-ABC-123")
    assert _form_field(route.calls.last.request.content, "record_locator") == "LOC-ABC-123"


@respx.mock
def test_crs_load_reservations_passes_xml_and_company_key() -> None:
    route = respx.post("https://api.tripit.example/v1/crsLoadReservations").mock(
        return_value=httpx.Response(200, content=_EMPTY)
    )
    payload = "<Request><Trip><display_name>x</display_name></Trip></Request>"
    with _client() as c:
        envelope = c.crs_load_reservations(payload, company_key="ck-99")
    assert envelope.trips == []
    req = route.calls.last.request
    assert _form_field(req.content, "company_key") == "ck-99"
    assert _form_field(req.content, "xml") == payload
