"""Trip + Response envelope parsing from XML."""

from __future__ import annotations

from pathlib import Path

from tripit.models import Response

XML = Path(__file__).parent / "fixtures" / "xml"


def _load(name: str) -> bytes:
    return (XML / name).read_bytes()


def test_list_trip_envelope_parses_multiple_trips() -> None:
    env = Response.from_xml(_load("list_trip_single_page.xml"))
    assert len(env.trips) == 2
    first = env.trips[0]
    assert first.display_name == "Seattle to New York"
    assert first.primary_location_address is not None
    assert first.primary_location_address.city == "New York"
    assert env.page_num == 1
    assert env.max_page == 1


def test_get_trip_single_object_parses() -> None:
    env = Response.from_xml(_load("get_trip_single.xml"))
    assert len(env.trips) == 1
    trip = env.trips[0]
    assert trip.id == "111"
    assert trip.trip_statuses is not None
    assert trip.trip_statuses.trip_statuses[0].status == "CONFIRMED"


def test_ids_parse_as_strings() -> None:
    env = Response.from_xml(_load("list_trip_single_page.xml"))
    assert env.trips[0].id == "111"
    assert isinstance(env.trips[0].id, str)


def test_warning_response_yields_warnings_and_trips() -> None:
    env = Response.from_xml(_load("warning_response.xml"))
    assert len(env.warnings) == 1
    assert env.warnings[0].entity_type == "Trip"
    assert len(env.trips) == 1


def test_error_response_yields_error_list() -> None:
    env = Response.from_xml(_load("error_response.xml"))
    assert len(env.errors) == 1
    assert env.errors[0].code == 404
    assert env.errors[0].entity_type == "Trip"


def test_trip_purposes_parse() -> None:
    env = Response.from_xml(_load("list_trip_single_page.xml"))
    second = env.trips[1]
    assert second.trip_purposes is not None
    assert second.trip_purposes.purpose_type_code == "B"


def test_roundtrip_preserves_data() -> None:
    env = Response.from_xml(_load("list_trip_single_page.xml"))
    again = Response.from_xml(env.to_xml(skip_empty=True))
    assert env.model_dump() == again.model_dump()
