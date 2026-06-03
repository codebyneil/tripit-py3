"""Write-path tests: model -> <Request> XML envelope + request-XSD validation."""

from __future__ import annotations

import pytest

from tripit.exceptions import TripItValidationError
from tripit.models import AirObject, AirSegment, NoteObject, Trip
from tripit.models.common import Address, DateTime
from tripit.xml import build_request_xml


def test_minimal_trip_serializes_to_request_envelope() -> None:
    trip = Trip(display_name="My Trip", start_date="2025-09-01", end_date="2025-09-05")
    xml = build_request_xml("Trip", trip)
    assert xml.startswith("<?xml")
    assert "<Request><Trip>" in xml
    assert "<display_name>My Trip</display_name>" in xml
    assert "<start_date>2025-09-01</start_date>" in xml


def test_address_nests_under_aliased_tag() -> None:
    trip = Trip(
        display_name="T",
        primary_location_address=Address(city="New York", state="NY", country="US"),
    )
    xml = build_request_xml("Trip", trip)
    assert "<PrimaryLocationAddress>" in xml
    assert "<city>New York</city>" in xml


def test_none_fields_are_omitted() -> None:
    trip = Trip(display_name="T")
    xml = build_request_xml("Trip", trip)
    assert "<start_date" not in xml  # unset -> omitted
    assert "<uuid" not in xml


def test_air_object_segments_emit_as_repeated_elements() -> None:
    air = AirObject(
        segments=[
            AirSegment(start_airport_code="SEA", end_airport_code="JFK"),
            AirSegment(start_airport_code="JFK", end_airport_code="LHR"),
        ]
    )
    xml = build_request_xml("AirObject", air)
    assert xml.count("<Segment>") == 2


def test_booleans_serialize_as_lowercase_strings() -> None:
    trip = Trip(display_name="T", is_private=True)
    xml = build_request_xml("Trip", trip)
    assert "<is_private>true</is_private>" in xml


def test_nested_datetime_serializes() -> None:
    air = AirObject(
        segments=[
            AirSegment(
                start_airport_code="SEA",
                start_date_time=DateTime(date="2025-09-01", time="08:00:00"),
            )
        ]
    )
    xml = build_request_xml("AirObject", air)
    assert "<StartDateTime>" in xml
    assert "<date>2025-09-01</date>" in xml


def test_note_object_serializes() -> None:
    note = NoteObject(display_name="n", text="hello world")
    xml = build_request_xml("NoteObject", note)
    assert "<Request><NoteObject>" in xml
    assert "<text>hello world</text>" in xml


def test_request_xsd_validation_rejects_unknown_tag() -> None:
    """A tag that isn't a valid Request child must fail XSD validation."""
    trip = Trip(display_name="T")
    with pytest.raises(TripItValidationError):
        build_request_xml("NotARealObject", trip)
