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

from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs

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

# Maps the XML object element name -> object-type name for harvesting IDs.
_OBJECT_ELEMENTS = {
    "AirObject": "air",
    "LodgingObject": "lodging",
    "CarObject": "car",
    "RailObject": "rail",
    "TransportObject": "transport",
    "CruiseObject": "cruise",
    "RestaurantObject": "restaurant",
    "ActivityObject": "activity",
    "NoteObject": "note",
    "MapObject": "map",
    "DirectionsObject": "directions",
    "ParkingObject": "parking",
}


@dataclass(frozen=True)
class CaptureSpec:
    """A single endpoint to hit + the filename to write the (scrubbed) result to."""

    method: str  # always "GET" today
    path: str  # e.g. "/v1/get/trip/id/12345"
    params: dict[str, str] = field(default_factory=dict)
    filename: str = ""  # e.g. "real_get_trip.xml"
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

    def _harvest_xml(xml_text: str) -> None:
        """Pluck trip + object IDs from a raw XML Response (no strict parsing).

        Discovery reads raw so it tolerates the out-of-schema elements that
        strict parsing rejects — capturing those is the whole point.
        """
        root = etree.fromstring(xml_text.encode("utf-8"))
        for trip in root.findall("Trip"):
            tid = trip.findtext("id")
            if tid and tid not in result.trip_ids:
                result.trip_ids.append(tid)
        for elem_name, type_name in _OBJECT_ELEMENTS.items():
            bucket = result.object_ids_by_type.setdefault(type_name, [])
            for obj in root.findall(elem_name):
                oid = obj.findtext("id")
                if oid and oid not in bucket:
                    bucket.append(oid)

    def _get_raw(path: str, params: dict[str, str]) -> str | None:
        try:
            return client._transport.request_raw("GET", path, params=params)
        except TripItError as exc:
            logger.warning("discovery %s %s failed: %s", path, params, exc)
            return None

    # list/trip?include_objects=true (upcoming + past) returns Trip[] plus every
    # nested object collection in one envelope.
    for past in (False, True):
        params = {"page_size": "25", "include_objects": "true", "page_num": "1"}
        if past:
            params["past"] = "true"
        raw = _get_raw("/v1/list/trip", params)
        if raw is not None:
            _harvest_xml(raw)

    # Also call list/object directly (past + upcoming) — catches objects not
    # nested under a trip in include_objects responses.
    for past in (False, True):
        params = {"page_size": "25", "page_num": "1"}
        if past:
            params["past"] = "true"
        raw = _get_raw("/v1/list/object", params)
        if raw is not None:
            _harvest_xml(raw)

    # Points programs — TripIt Pro only; tolerate failure.
    raw = _get_raw("/v1/list/points_program", {})
    if raw is not None:
        root = etree.fromstring(raw.encode("utf-8"))
        programs = root.findall("PointsProgram")
        result.is_pro = bool(programs)
        for prog in programs:
            pid = prog.findtext("id")
            if pid:
                result.points_program_ids.append(pid)

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
        CaptureSpec("GET", "/v1/get/profile", filename="real_get_profile.xml", category="profile")
    )

    # 2. Points programs (Pro only)
    if disc.is_pro:
        yield from emit(
            CaptureSpec(
                "GET",
                "/v1/list/points_program",
                filename="real_list_points_program.xml",
                category="points",
            )
        )
        if disc.points_program_ids:
            first = disc.points_program_ids[0]
            yield from emit(
                CaptureSpec(
                    "GET",
                    f"/v1/get/points_program/id/{first}",
                    filename="real_get_points_program.xml",
                    category="points",
                )
            )

    # 3. Trips
    yield from emit(
        CaptureSpec("GET", "/v1/list/trip", filename="real_list_trip_upcoming.xml", category="trip")
    )
    yield from emit(
        CaptureSpec(
            "GET",
            "/v1/list/trip",
            params={"past": "true"},
            filename="real_list_trip_past.xml",
            category="trip",
        )
    )
    yield from emit(
        CaptureSpec(
            "GET",
            "/v1/list/trip",
            params={"include_objects": "true"},
            filename="real_list_trip_with_objects.xml",
            category="trip",
        )
    )
    if disc.trip_ids:
        first = disc.trip_ids[0]
        yield from emit(
            CaptureSpec(
                "GET",
                f"/v1/get/trip/id/{first}",
                filename="real_get_trip.xml",
                category="trip",
            )
        )
        yield from emit(
            CaptureSpec(
                "GET",
                f"/v1/get/trip/id/{first}",
                params={"include_objects": "true"},
                filename="real_get_trip_with_objects.xml",
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
                filename=f"real_list_object_{type_name}.xml",
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
                filename=f"real_get_{type_name}.xml",
                category="object",
            )
        )
