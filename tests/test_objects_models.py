"""Round-trip parsing tests for the Phase 2 object models."""

from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path
from typing import Any

from tripit.models.envelope import Response
from tripit.models.objects import AirObject

FIXTURES = Path(__file__).parent / "fixtures" / "json"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())["Response"]


def test_air_object_parses_with_typed_segment_and_traveler() -> None:
    envelope = Response.model_validate(_load("get_air.json"))
    assert len(envelope.air_objects) == 1
    air = envelope.air_objects[0]
    assert isinstance(air, AirObject)
    assert air.id == "555111"
    assert air.trip_id == "999000111222"
    assert air.is_purchased is True
    assert air.supplier_name == "Air Canada"
    assert len(air.segments) == 1
    seg = air.segments[0]
    assert seg.start_airport_code == "YYZ"
    assert seg.end_airport_code == "NRT"
    assert seg.start_date_time is not None
    assert seg.start_date_time.date == date(2026, 5, 1)
    assert seg.start_date_time.time == time(8, 0)
    assert seg.start_date_time.timezone == "America/Toronto"
    assert seg.status is not None
    assert seg.status.flight_status == "301"
    # `Traveler` came in as a bare object — auto-wrapped into a list.
    assert len(air.travelers) == 1
    assert air.travelers[0].first_name == "Neil"


def test_profile_parses_with_email_addresses() -> None:
    envelope = Response.model_validate(_load("get_profile.json"))
    assert len(envelope.profiles) == 1
    profile = envelope.profiles[0]
    assert profile.screen_name == "neilauto"
    assert profile.is_client is True
    assert profile.is_pro is False
    assert profile.home_airport == "YYZ"
    assert profile.profile_email_addresses is not None
    addrs = profile.profile_email_addresses.profile_email_addresses
    assert len(addrs) == 1
    assert addrs[0].address == "neil@autumnlabs.com"
    assert addrs[0].is_auto_import is True


def test_profile_lifts_at_attributes_ref() -> None:
    """TripIt's JSON encoding represents XML attributes as a nested dict.

    `Profile.ref` (declared as XML attribute `ref` in the XSD) arrives as
    `{"@attributes": {"ref": "..."}}` in the JSON payload. The model must
    lift that into the canonical `ref` field.
    """
    from tripit.models.profile import Profile

    payload = {
        "@attributes": {"ref": "ryZ03lKSXLWI67EaT_EdRA"},
        "is_client": "true",
        "screen_name": "test",
    }
    profile = Profile.model_validate(payload)
    assert profile.ref == "ryZ03lKSXLWI67EaT_EdRA"
    assert profile.is_client is True
    assert profile.screen_name == "test"


def test_profile_accepts_plain_ref_field() -> None:
    """Round-tripping via model_dump emits `ref` directly; must re-parse."""
    from tripit.models.profile import Profile

    profile = Profile.model_validate({"ref": "abc", "screen_name": "s"})
    assert profile.ref == "abc"


def test_profile_handles_missing_attributes_gracefully() -> None:
    from tripit.models.profile import Profile

    profile = Profile.model_validate({"screen_name": "s"})
    assert profile.ref is None


def test_points_programs_list_parses_with_string_ids() -> None:
    envelope = Response.model_validate(_load("list_points_program.json"))
    assert len(envelope.points_programs) == 2
    aeroplan = envelope.points_programs[0]
    assert aeroplan.id == "111"
    assert aeroplan.name == "Aeroplan"
    assert aeroplan.balance == "85000"
