"""Discovery + per-spec capture matrix for the fixture-capture script.

Two pieces:
- `discovery_pass(client)` issues a small set of "what does this account have?"
  queries to harvest IDs we'll then capture against.
- `iter_capture_specs(disc)` yields a `CaptureSpec` per endpoint we should hit,
  filtered to whatever the account actually has.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from tripit import TripIt
from tripit.exceptions import TripItError

logger = logging.getLogger("tripit.capture")

# Object types we expect to find on real trips. Matches /v1/list/object?type=<t>
# values and /v1/get/<t>/id/<id> paths.
OBJECT_TYPES: tuple[str, ...] = (
    "air",
    "lodging",
    "car",
    "rail",
    "transport",
    "cruise",
    "restaurant",
    "activity",
    "note",
    "map",
    "directions",
    "parking",
)

# Maps Response.<attr> -> object-type name for harvesting IDs from include_objects=true responses.
_OBJECT_FIELDS = {
    "air_objects": "air",
    "lodging_objects": "lodging",
    "car_objects": "car",
    "rail_objects": "rail",
    "transport_objects": "transport",
    "cruise_objects": "cruise",
    "restaurant_objects": "restaurant",
    "activity_objects": "activity",
    "note_objects": "note",
    "map_objects": "map",
    "directions_objects": "directions",
    "parking_objects": "parking",
}


@dataclass(frozen=True)
class CaptureSpec:
    """A single endpoint to hit + the filename to write the (scrubbed) result to."""

    method: str  # always "GET" today
    path: str  # e.g. "/v1/get/trip/id/12345"
    params: dict[str, str] = field(default_factory=dict)
    filename: str = ""  # e.g. "real_get_trip.json"
    category: str = ""  # "profile" | "points" | "trip" | "object" | "list_object"


@dataclass
class DiscoveryResult:
    trip_ids: list[str] = field(default_factory=list)
    object_ids_by_type: dict[str, list[str]] = field(default_factory=dict)
    points_program_ids: list[str] = field(default_factory=list)
    is_pro: bool = False


def discovery_pass(client: TripIt) -> DiscoveryResult:
    """Harvest trip + object IDs by walking list/trip and list/object envelopes.

    `list/trip?include_objects=true` returns the full Response envelope with
    Trip[] AND every nested object collection. We use it to harvest both at
    once (one round trip per past/upcoming variant). For belt-and-suspenders
    coverage we also call list/object directly, which is the API surface used
    when no specific trip is selected.
    """
    result = DiscoveryResult()

    # Helper: pluck trip IDs + object IDs from a single Response envelope.
    def _harvest_from(envelope: Any) -> None:
        for trip in getattr(envelope, "trips", []) or []:
            tid = getattr(trip, "id", None)
            if tid and tid not in result.trip_ids:
                result.trip_ids.append(tid)
        for attr, type_name in _OBJECT_FIELDS.items():
            bucket = result.object_ids_by_type.setdefault(type_name, [])
            for obj in getattr(envelope, attr, []) or []:
                oid = getattr(obj, "id", None)
                if oid and oid not in bucket:
                    bucket.append(oid)

    # list/trip?include_objects=true (upcoming + past) returns the full
    # envelope. Use list_trips_envelope-style iteration via the transport
    # directly, since the typed client's list_trips() drops nested objects.
    for past in (False, True):
        params = {
            "page_size": "25",
            "include_objects": "true",
            "page_num": "1",
        }
        if past:
            params["past"] = "true"
        try:
            raw = client._transport.request_raw("GET", "/v1/list/trip", params=params)
        except TripItError as exc:
            logger.warning("list/trip include_objects (past=%s) failed: %s", past, exc)
            continue
        try:
            from tripit.models.envelope import Response

            envelope = Response.model_validate(raw.get("Response", raw))
        except Exception as exc:
            logger.warning("Couldn't parse list/trip envelope (past=%s): %s", past, exc)
            continue
        _harvest_from(envelope)

    # Also call list/object directly (past + upcoming) — catches objects
    # not nested under a trip in include_objects responses.
    for past in (False, True):
        try:
            for envelope in client.list_objects_envelope(past=past, page_size=25):
                _harvest_from(envelope)
        except TripItError as exc:
            logger.warning("list_objects discovery (past=%s) failed: %s", past, exc)

    # Points programs — TripIt Pro only; tolerate failure.
    try:
        programs = client.list_points_programs()
        result.is_pro = True
        for prog in programs:
            if prog.id:
                result.points_program_ids.append(prog.id)
    except TripItError as exc:
        logger.info("list_points_programs unavailable (non-Pro account?): %s", exc)
        result.is_pro = False

    return result


def iter_capture_specs(
    disc: DiscoveryResult, only: set[str] | None = None
) -> Iterator[CaptureSpec]:
    """Yield the capture specs for everything the account exposes.

    `only` restricts to categories — e.g. `only={"trip", "object"}` skips
    profile/points. Empty/None means emit all categories.
    """

    def emit(spec: CaptureSpec) -> Iterator[CaptureSpec]:
        if not only or spec.category in only:
            yield spec

    # 1. Profile (always)
    yield from emit(
        CaptureSpec("GET", "/v1/get/profile", filename="real_get_profile.json", category="profile")
    )

    # 2. Points programs (Pro only)
    if disc.is_pro:
        yield from emit(
            CaptureSpec(
                "GET",
                "/v1/list/points_program",
                filename="real_list_points_program.json",
                category="points",
            )
        )
        if disc.points_program_ids:
            first = disc.points_program_ids[0]
            yield from emit(
                CaptureSpec(
                    "GET",
                    f"/v1/get/points_program/id/{first}",
                    filename="real_get_points_program.json",
                    category="points",
                )
            )

    # 3. Trips
    yield from emit(
        CaptureSpec(
            "GET", "/v1/list/trip", filename="real_list_trip_upcoming.json", category="trip"
        )
    )
    yield from emit(
        CaptureSpec(
            "GET",
            "/v1/list/trip",
            params={"past": "true"},
            filename="real_list_trip_past.json",
            category="trip",
        )
    )
    yield from emit(
        CaptureSpec(
            "GET",
            "/v1/list/trip",
            params={"include_objects": "true"},
            filename="real_list_trip_with_objects.json",
            category="trip",
        )
    )
    if disc.trip_ids:
        first = disc.trip_ids[0]
        yield from emit(
            CaptureSpec(
                "GET",
                f"/v1/get/trip/id/{first}",
                filename="real_get_trip.json",
                category="trip",
            )
        )
        yield from emit(
            CaptureSpec(
                "GET",
                f"/v1/get/trip/id/{first}",
                params={"include_objects": "true"},
                filename="real_get_trip_with_objects.json",
                category="trip",
            )
        )

    # 4. Per-type list/object
    for type_name in OBJECT_TYPES:
        ids = disc.object_ids_by_type.get(type_name, [])
        if not ids:
            continue
        yield from emit(
            CaptureSpec(
                "GET",
                "/v1/list/object",
                params={"type": type_name},
                filename=f"real_list_object_{type_name}.json",
                category="list_object",
            )
        )

    # 5. Per-type get single
    for type_name in OBJECT_TYPES:
        ids = disc.object_ids_by_type.get(type_name, [])
        if not ids:
            continue
        yield from emit(
            CaptureSpec(
                "GET",
                f"/v1/get/{type_name}/id/{ids[0]}",
                filename=f"real_get_{type_name}.json",
                category="object",
            )
        )


