"""Tests for the fixture-capture scrubber.

Covers:
- Determinism: same input scrubs to same output, every time.
- Cross-fixture stability: same email appearing in two records scrubs identically.
- Field-set membership: scrub only changes values, never adds or removes keys.
- Preservation: cities, dates, IDs, lat/lon, airport codes pass through.
- Email-record detection: ProfileEmailAddress's `address` is treated as email.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # make `scripts` importable

from scripts._capture.scrub import scrub  # noqa: E402


def test_determinism_same_input_same_output() -> None:
    payload = {"first_name": "Alice", "last_name": "Liddell"}
    assert scrub(payload) == scrub(payload)


def test_cross_record_stability_for_same_email() -> None:
    payload = {
        "ProfileEmailAddresses": {
            "ProfileEmailAddress": [
                {
                    "uuid": "u1",
                    "uuid_ref": "ur1",
                    "address": "neil@example.com",
                    "is_auto_import": "true",
                    "is_confirmed": "true",
                },
                {
                    "uuid": "u2",
                    "uuid_ref": "ur2",
                    "address": "neil@example.com",
                    "is_auto_import": "false",
                    "is_confirmed": "true",
                },
            ]
        }
    }
    result = scrub(payload)
    addrs = result["ProfileEmailAddresses"]["ProfileEmailAddress"]
    assert addrs[0]["address"] == addrs[1]["address"]  # same scrubbed value
    assert addrs[0]["address"].endswith("@example.invalid")


def test_email_address_in_supplier_context_uses_email_path() -> None:
    payload = {"supplier_email_address": "boss@hotel.com"}
    result = scrub(payload)
    assert result["supplier_email_address"].endswith("@example.invalid")


def test_address_without_email_siblings_is_left_alone() -> None:
    """A trip's `primary_location_address` has an `address` line that's a street
    description, not an email — must not get scrubbed as email."""
    payload = {
        "PrimaryLocationAddress": {
            "city": "Berlin",
            "country": "DE",
            "address": "Unter den Linden 1",  # street-like, no email siblings
        }
    }
    result = scrub(payload)
    assert result["PrimaryLocationAddress"]["address"] == "Unter den Linden 1"


def test_preserves_cities_dates_ids_lat_lon_airport_codes() -> None:
    payload = {
        "id": "999000111222",
        "uuid": "abc-def-123",
        "start_date": "2026-05-01",
        "primary_location": "Tokyo, JP",
        "PrimaryLocationAddress": {
            "city": "Tokyo",
            "country": "JP",
            "latitude": "35.6762",
            "longitude": "139.6503",
        },
        "Segment": {
            "start_airport_code": "YYZ",
            "end_airport_code": "NRT",
            "marketing_airline_code": "AC",
            "marketing_flight_number": "23",
        },
        "record_locator": "ABC123",
    }
    assert scrub(payload) == payload


def test_scrubs_name_fields() -> None:
    payload = {
        "Traveler": {
            "first_name": "Neil",
            "middle_name": "Q",
            "last_name": "Autumn",
        },
        "screen_name": "neilauto",
        "public_display_name": "Neil A.",
    }
    result = scrub(payload)
    for v in [
        result["Traveler"]["first_name"],
        result["Traveler"]["middle_name"],
        result["Traveler"]["last_name"],
        result["screen_name"],
        result["public_display_name"],
    ]:
        assert v.startswith("Person ")


def test_scrubs_phone_and_street_fields() -> None:
    payload = {
        "supplier_phone": "+1-416-555-1234",
        "Address": {
            "addr1": "123 Main St",
            "addr2": "Apt 4B",
            "city": "Toronto",
            "country": "CA",
        },
    }
    result = scrub(payload)
    assert result["supplier_phone"].startswith("+1-555-555-")
    assert "Street" in result["Address"]["addr1"]
    assert "Street" in result["Address"]["addr2"]
    # City + country preserved.
    assert result["Address"]["city"] == "Toronto"
    assert result["Address"]["country"] == "CA"


def test_scrub_does_not_change_key_set() -> None:
    payload = {
        "Traveler": {"first_name": "X", "last_name": "Y", "ticket_num": "T1"},
        "id": "1",
    }
    result = scrub(payload)
    assert set(result.keys()) == set(payload.keys())
    assert set(result["Traveler"].keys()) == set(payload["Traveler"].keys())


def test_scrub_handles_lists_recursively() -> None:
    payload = {
        "Traveler": [
            {"first_name": "A"},
            {"first_name": "B"},
        ]
    }
    result = scrub(payload)
    assert result["Traveler"][0]["first_name"].startswith("Person ")
    assert result["Traveler"][1]["first_name"].startswith("Person ")
    assert result["Traveler"][0]["first_name"] != result["Traveler"][1]["first_name"]


def test_scrub_passes_through_non_string_scalars() -> None:
    payload = {"is_pro": True, "timestamp": 1700000000, "latitude": 35.6762}
    assert scrub(payload) == payload
