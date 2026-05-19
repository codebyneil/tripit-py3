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
    """Harvest IDs from the live account so the spec matrix can target them.

    All discovery calls go through the typed client (they only need IDs, not
    raw JSON), so any TripIt-emitted field that the models drop is fine here.
    """
    result = DiscoveryResult()

    # Upcoming trips with all objects nested.
    try:
        for trip in client.list_trips(include_objects=True, page_size=25):
            if trip.id:
                result.trip_ids.append(trip.id)
    except TripItError as exc:
        logger.warning("list_trips upcoming failed: %s", exc)

    # Past trips, also with objects.
    try:
        for trip in client.list_trips(past=True, include_objects=True, page_size=25):
            if trip.id and trip.id not in result.trip_ids:
                result.trip_ids.append(trip.id)
    except TripItError as exc:
        logger.warning("list_trips past failed: %s", exc)

    # Object IDs — pull from the include_objects envelope via list_objects_envelope.
    try:
        for envelope in client.list_objects_envelope(page_size=25):
            for attr, type_name in _OBJECT_FIELDS.items():
                bucket = result.object_ids_by_type.setdefault(type_name, [])
                for obj in getattr(envelope, attr, []) or []:
                    oid = getattr(obj, "id", None)
                    if oid and oid not in bucket:
                        bucket.append(oid)
    except TripItError as exc:
        logger.warning("list_objects discovery failed: %s", exc)

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


def harvest_object_ids_from_envelope(envelope: Any, dest: dict[str, list[str]]) -> None:
    """Pluck one id per object type from a Response envelope into `dest`."""
    for attr, type_name in _OBJECT_FIELDS.items():
        bucket = dest.setdefault(type_name, [])
        for obj in getattr(envelope, attr, []) or []:
            oid = getattr(obj, "id", None)
            if oid and oid not in bucket:
                bucket.append(oid)
