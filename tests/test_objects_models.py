"""Parsing tests for object + profile + points models from XML."""

from __future__ import annotations

from pathlib import Path

from tripit.models import Profile, Response

XML = Path(__file__).parent / "fixtures" / "xml"


def _load(name: str) -> bytes:
    return (XML / name).read_bytes()


def test_air_object_parses_with_typed_segment_and_traveler() -> None:
    env = Response.from_xml(_load("get_air.xml"))
    assert len(env.air_objects) == 1
    air = env.air_objects[0]
    assert air.record_locator == "ABC123"
    assert air.is_purchased is True
    assert len(air.segments) == 1
    seg = air.segments[0]
    assert seg.start_airport_code == "SEA"
    assert seg.start_date_time is not None
    assert seg.start_date_time.utc_offset == "-07:00"
    assert seg.status is not None
    assert seg.status.flight_status == "301"
    assert len(air.travelers) == 1
    assert air.travelers[0].first_name == "Neil"


def test_air_segment_decimal_coercion() -> None:
    env = Response.from_xml(_load("get_air.xml"))
    seg = env.air_objects[0].segments[0]
    assert float(seg.start_airport_latitude) == 47.443839


def test_profile_parses_with_ref_attribute_and_emails() -> None:
    env = Response.from_xml(_load("get_profile.xml"))
    assert len(env.profiles) == 1
    prof = env.profiles[0]
    assert prof.ref == "C0FFEE"
    assert prof.is_pro is True
    assert prof.home_airport == "SEA"
    assert prof.profile_email_addresses is not None
    emails = prof.profile_email_addresses.profile_email_addresses
    assert emails[0].address == "neil@example.com"
    assert emails[0].is_primary is True


def test_profile_from_xml_direct() -> None:
    prof = Profile.from_xml(
        b'<Profile ref="X1"><is_client>false</is_client><is_pro>false</is_pro>'
        b"<screen_name>s</screen_name><public_display_name>S</public_display_name>"
        b"<profile_url>/u</profile_url></Profile>"
    )
    assert prof.ref == "X1"
    assert prof.is_pro is False


def test_points_programs_parse_with_string_ids() -> None:
    env = Response.from_xml(_load("list_points_program.xml"))
    assert len(env.points_programs) == 2
    first = env.points_programs[0]
    assert first.id == "5001"
    assert first.name == "Alaska Mileage Plan"
    assert len(first.activities) == 1
    assert first.activities[0].total == "2400"
