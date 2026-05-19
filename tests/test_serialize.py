"""Tests for the pydantic → `<Request>` XML serializer."""

from __future__ import annotations

from datetime import date

from lxml import etree

from tripit.models.common import Address, DateTime
from tripit.models.objects import AirObject, AirSegment, NoteObject
from tripit.models.trip import Trip
from tripit.serialize import _stringify, model_to_request_xml


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


def test_minimal_trip_serializes_to_request_envelope() -> None:
    trip = Trip(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        display_name="Smoke test",
        primary_location="Tokyo, JP",
    )
    xml = model_to_request_xml("Trip", trip)
    root = _parse(xml)
    assert root.tag == "Request"
    inner = root.find("Trip")
    assert inner is not None
    assert inner.findtext("display_name") == "Smoke test"
    assert inner.findtext("primary_location") == "Tokyo, JP"
    assert inner.findtext("start_date") == "2026-06-01"
    assert inner.findtext("end_date") == "2026-06-03"


def test_trip_with_primary_location_address_nests_correctly() -> None:
    trip = Trip(
        display_name="X",
        primary_location_address=Address(city="Berlin", country="DE"),
    )
    xml = model_to_request_xml("Trip", trip)
    root = _parse(xml)
    addr = root.find("Trip/PrimaryLocationAddress")
    assert addr is not None
    assert addr.findtext("city") == "Berlin"
    assert addr.findtext("country") == "DE"


def test_none_fields_are_omitted() -> None:
    trip = Trip(display_name="Just a name")
    xml = model_to_request_xml("Trip", trip)
    root = _parse(xml)
    trip_el = root.find("Trip")
    assert trip_el is not None
    # Only `display_name` should be present — None fields excluded.
    children = [c.tag for c in trip_el]
    assert children == ["display_name"]


def test_air_object_segments_emit_as_repeated_elements() -> None:
    air = AirObject(
        supplier_name="Air Canada",
        record_locator="ABC123",
        segments=[
            AirSegment(
                start_airport_code="YYZ",
                end_airport_code="NRT",
                start_date_time=DateTime(date=date(2026, 5, 1)),
            ),
            AirSegment(
                start_airport_code="NRT",
                end_airport_code="YYZ",
                start_date_time=DateTime(date=date(2026, 5, 10)),
            ),
        ],
    )
    xml = model_to_request_xml("AirObject", air)
    root = _parse(xml)
    segs = root.findall("AirObject/Segment")
    assert len(segs) == 2
    assert segs[0].findtext("start_airport_code") == "YYZ"
    assert segs[0].findtext("end_airport_code") == "NRT"
    assert segs[1].findtext("start_airport_code") == "NRT"
    assert root.findtext("AirObject/supplier_name") == "Air Canada"


def test_booleans_serialize_as_lowercase_strings() -> None:
    note = NoteObject(display_name="memo", is_client_traveler=True)
    xml = model_to_request_xml("NoteObject", note)
    root = _parse(xml)
    assert root.findtext("NoteObject/is_client_traveler") == "true"


def test_stringify_handles_basic_types() -> None:
    assert _stringify(True) == "true"
    assert _stringify(False) == "false"
    assert _stringify(42) == "42"
    assert _stringify(date(2026, 5, 1)) == "2026-05-01"


def test_xml_has_declaration_and_utf8_encoding() -> None:
    trip = Trip(display_name="x")
    xml = model_to_request_xml("Trip", trip)
    assert xml.startswith("<?xml")
    assert "UTF-8" in xml[:60]
