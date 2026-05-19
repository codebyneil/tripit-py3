"""Model parsing & round-trip tests for envelope + Trip."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tripit.models.envelope import Response
from tripit.models.trip import Trip

FIXTURES = Path(__file__).parent / "fixtures" / "json"


def _load(name: str) -> Any:
    import json

    with (FIXTURES / name).open() as f:
        return json.load(f)["Response"]


def test_list_trip_envelope_parses_multiple_trips() -> None:
    envelope = Response.model_validate(_load("list_trip_single_page.json"))
    assert len(envelope.trips) == 2
    first = envelope.trips[0]
    assert first.id == "999000111222"
    assert first.display_name == "Tokyo Vacation"
    assert first.start_date == date(2026, 5, 1)
    assert first.is_private is False
    assert first.is_pro_enabled is True
    assert first.primary_location_address is not None
    assert first.primary_location_address.city == "Tokyo"
    assert first.primary_location_address.country == "JP"


def test_get_trip_single_object_is_wrapped_into_list() -> None:
    """TripIt sometimes returns `Trip` as a bare object instead of a list."""
    envelope = Response.model_validate(_load("get_trip_single.json"))
    assert len(envelope.trips) == 1
    assert envelope.trips[0].id == "999000111222"


def test_integer_id_is_coerced_to_string() -> None:
    """The fixture has id as a raw integer; we should still see a str."""
    envelope = Response.model_validate(_load("get_trip_single.json"))
    assert isinstance(envelope.trips[0].id, str)


def test_warning_response_yields_no_trips_and_warnings_list() -> None:
    envelope = Response.model_validate(_load("warning_response.json"))
    assert envelope.trips == []
    assert len(envelope.warnings) == 1
    assert envelope.warnings[0].entity_type == "Trip"


def test_error_response_yields_error_list() -> None:
    envelope = Response.model_validate(_load("error_response.json"))
    assert len(envelope.errors) == 1
    assert envelope.errors[0].code == 404


def test_trip_model_accepts_aliased_payload() -> None:
    payload = {
        "id": "1",
        "PrimaryLocationAddress": {"city": "Berlin"},
    }
    trip = Trip.model_validate(payload)
    assert trip.primary_location_address is not None
    assert trip.primary_location_address.city == "Berlin"


def test_trip_model_round_trip_preserves_aliases() -> None:
    payload: dict[str, Any] = {
        "id": "1",
        "start_date": "2026-05-01",
        "PrimaryLocationAddress": {"city": "Berlin"},
    }
    trip = Trip.model_validate(payload)
    dumped = trip.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert dumped["PrimaryLocationAddress"]["city"] == "Berlin"
