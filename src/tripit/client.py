"""TripIt client.

Phase 1 wired up `get_trip` and `list_trips`. Phase 2 fills in the remaining
read endpoints: `get_profile`, `get_points_program`, `list_points_programs`,
`list_objects`, and every `get_<entity>` for the 12 object types.

Writes (`create_*`, `replace_*`, `delete_*`, CRS) are Phase 3.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal, Self

from tripit.auth import OAuth1Auth
from tripit.exceptions import TripItNotFoundError
from tripit.models.envelope import Response
from tripit.models.objects import (
    ActivityObject,
    AirObject,
    CarObject,
    CruiseObject,
    DirectionsObject,
    LodgingObject,
    MapObject,
    NoteObject,
    ParkingObject,
    RailObject,
    RestaurantObject,
    TransportObject,
)
from tripit.models.points import PointsProgram
from tripit.models.profile import Profile
from tripit.models.trip import Trip
from tripit.pagination import paginate
from tripit.transport import DEFAULT_API_URL, _Transport

ObjectTypeName = Literal[
    "all",
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
]


class TripIt:
    """High-level TripIt v1 API client."""

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        token: str,
        token_secret: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float | None = 30.0,
        user_agent: str | None = None,
    ) -> None:
        auth = OAuth1Auth(
            consumer_key,
            consumer_secret,
            token=token,
            token_secret=token_secret,
        )
        self._transport = _Transport(
            auth,
            api_url=api_url,
            timeout=timeout,
            user_agent=user_agent,
        )

    @classmethod
    def two_legged(
        cls,
        consumer_key: str,
        consumer_secret: str,
        requestor_id: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float | None = 30.0,
        user_agent: str | None = None,
    ) -> Self:
        """Construct a client using a 2-legged credential (no per-user token)."""
        instance = cls.__new__(cls)
        auth = OAuth1Auth(
            consumer_key,
            consumer_secret,
            requestor_id=requestor_id,
        )
        instance._transport = _Transport(
            auth,
            api_url=api_url,
            timeout=timeout,
            user_agent=user_agent,
        )
        return instance

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ----- Trip reads -----

    def get_trip(self, trip_id: str, *, include_objects: bool = False) -> Trip:
        """Fetch a single Trip by id. Raises `TripItNotFoundError` if missing."""
        params: dict[str, Any] = {"id": str(trip_id)}
        if include_objects:
            params["include_objects"] = "true"
        envelope = self._transport.request_json("GET", "/v1/get/trip", params=params)
        if not envelope.trips:
            raise TripItNotFoundError(f"Trip {trip_id} not in response", status_code=404)
        return envelope.trips[0]

    def list_trips(
        self,
        *,
        traveler: Literal["true", "false", "only"] | None = None,
        past: bool = False,
        modified_since: int | None = None,
        include_objects: bool = False,
        page_size: int = 25,
    ) -> Iterator[Trip]:
        """Yield all Trips matching the filter, paging transparently."""
        base_params: dict[str, Any] = {"page_size": str(page_size)}
        if traveler is not None:
            base_params["traveler"] = traveler
        if past:
            base_params["past"] = "true"
        if modified_since is not None:
            base_params["modified_since"] = str(modified_since)
        if include_objects:
            base_params["include_objects"] = "true"

        def fetch_page(page_num: int) -> Response:
            return self._transport.request_json(
                "GET",
                "/v1/list/trip",
                params={**base_params, "page_num": str(page_num)},
            )

        yield from paginate(fetch_page, lambda r: r.trips)

    # ----- Profile & points -----

    def get_profile(self) -> Profile:
        envelope = self._transport.request_json("GET", "/v1/get/profile")
        if not envelope.profiles:
            raise TripItNotFoundError("No profile in response", status_code=404)
        return envelope.profiles[0]

    def get_points_program(self, program_id: str) -> PointsProgram:
        envelope = self._transport.request_json(
            "GET", "/v1/get/points_program", params={"id": str(program_id)}
        )
        if not envelope.points_programs:
            raise TripItNotFoundError(
                f"PointsProgram {program_id} not in response", status_code=404
            )
        return envelope.points_programs[0]

    def list_points_programs(self) -> list[PointsProgram]:
        envelope = self._transport.request_json("GET", "/v1/list/points_program")
        return envelope.points_programs

    # ----- Reservation object reads -----

    def _get_single(self, entity: str, object_id: str, pluck: str) -> Any:
        envelope = self._transport.request_json(
            "GET", f"/v1/get/{entity}", params={"id": str(object_id)}
        )
        items = getattr(envelope, pluck)
        if not items:
            raise TripItNotFoundError(f"{entity} {object_id} not in response", status_code=404)
        return items[0]

    def get_air(self, segment_id: str) -> AirObject:
        return self._get_single("air", segment_id, "air_objects")

    def get_lodging(self, lodging_id: str) -> LodgingObject:
        return self._get_single("lodging", lodging_id, "lodging_objects")

    def get_car(self, car_id: str) -> CarObject:
        return self._get_single("car", car_id, "car_objects")

    def get_rail(self, rail_id: str) -> RailObject:
        return self._get_single("rail", rail_id, "rail_objects")

    def get_transport(self, transport_id: str) -> TransportObject:
        return self._get_single("transport", transport_id, "transport_objects")

    def get_cruise(self, cruise_id: str) -> CruiseObject:
        return self._get_single("cruise", cruise_id, "cruise_objects")

    def get_restaurant(self, restaurant_id: str) -> RestaurantObject:
        return self._get_single("restaurant", restaurant_id, "restaurant_objects")

    def get_activity(self, activity_id: str) -> ActivityObject:
        return self._get_single("activity", activity_id, "activity_objects")

    def get_note(self, note_id: str) -> NoteObject:
        return self._get_single("note", note_id, "note_objects")

    def get_map(self, map_id: str) -> MapObject:
        return self._get_single("map", map_id, "map_objects")

    def get_directions(self, directions_id: str) -> DirectionsObject:
        return self._get_single("directions", directions_id, "directions_objects")

    def get_parking(self, parking_id: str) -> ParkingObject:
        return self._get_single("parking", parking_id, "parking_objects")

    # ----- list/object multi-type read -----

    def list_objects_envelope(
        self,
        *,
        type: ObjectTypeName | None = None,
        trip_id: str | None = None,
        past: bool = False,
        modified_since: int | None = None,
        include_objects: bool = False,
        page_size: int = 25,
    ) -> Iterator[Response]:
        """Yield each page envelope. Useful when callers want every object kind."""
        base_params: dict[str, Any] = {"page_size": str(page_size)}
        if type is not None:
            base_params["type"] = type
        if trip_id is not None:
            base_params["trip_id"] = str(trip_id)
        if past:
            base_params["past"] = "true"
        if modified_since is not None:
            base_params["modified_since"] = str(modified_since)
        if include_objects:
            base_params["include_objects"] = "true"

        page = 1
        while True:
            envelope = self._transport.request_json(
                "GET",
                "/v1/list/object",
                params={**base_params, "page_num": str(page)},
            )
            yield envelope
            max_page = envelope.max_page or 1
            if page >= max_page:
                return
            page += 1
