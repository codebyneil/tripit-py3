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
from tripit.xml import build_request_xml

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
        validate_responses: bool = False,
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
            validate_responses=validate_responses,
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
        validate_responses: bool = False,
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
            validate_responses=validate_responses,
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
        params: dict[str, Any] = {}
        if include_objects:
            params["include_objects"] = "true"
        envelope = self._transport.request_xml(
            "GET", f"/v1/get/trip/id/{trip_id}", params=params or None
        )
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
            return self._transport.request_xml(
                "GET",
                "/v1/list/trip",
                params={**base_params, "page_num": str(page_num)},
            )

        yield from paginate(fetch_page, lambda r: r.trips)

    # ----- Profile & points -----

    def get_profile(self) -> Profile:
        envelope = self._transport.request_xml("GET", "/v1/get/profile")
        if not envelope.profiles:
            raise TripItNotFoundError("No profile in response", status_code=404)
        return envelope.profiles[0]

    def get_points_program(self, program_id: str) -> PointsProgram:
        envelope = self._transport.request_xml("GET", f"/v1/get/points_program/id/{program_id}")
        if not envelope.points_programs:
            raise TripItNotFoundError(
                f"PointsProgram {program_id} not in response", status_code=404
            )
        return envelope.points_programs[0]

    def list_points_programs(self) -> list[PointsProgram]:
        envelope = self._transport.request_xml("GET", "/v1/list/points_program")
        return envelope.points_programs

    # ----- Reservation object reads -----

    def _get_single(self, entity: str, object_id: str, pluck: str) -> Any:
        envelope = self._transport.request_xml("GET", f"/v1/get/{entity}/id/{object_id}")
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

    # ----- Writes (create / replace / delete) -----

    def _create(self, tag: str, model: Any, pluck: str) -> Any:
        """POST /v1/create with the serialized model. Returns the created object."""
        xml = build_request_xml(tag, model)
        envelope = self._transport.request_xml("POST", "/v1/create", data={"xml": xml})
        items = getattr(envelope, pluck)
        if not items:
            raise TripItNotFoundError(f"Created {tag} not echoed back in response", status_code=200)
        return items[0]

    def _replace(self, entity: str, tag: str, object_id: str, model: Any, pluck: str) -> Any:
        """POST /v1/replace/<entity>/id/<id> with the serialized model."""
        xml = build_request_xml(tag, model)
        envelope = self._transport.request_xml(
            "POST", f"/v1/replace/{entity}/id/{object_id}", data={"xml": xml}
        )
        items = getattr(envelope, pluck)
        if not items:
            raise TripItNotFoundError(
                f"Replaced {entity} {object_id} not echoed back", status_code=200
            )
        return items[0]

    def _delete(self, entity: str, object_id: str) -> None:
        # TripIt's documented delete is a GET to /v1/delete/<entity>/id/<id>.
        self._transport.request_xml("GET", f"/v1/delete/{entity}/id/{object_id}")

    # Trip
    def create_trip(self, trip: Trip) -> Trip:
        return self._create("Trip", trip, "trips")

    def replace_trip(self, trip_id: str, trip: Trip) -> Trip:
        return self._replace("trip", "Trip", trip_id, trip, "trips")

    def delete_trip(self, trip_id: str) -> None:
        self._delete("trip", trip_id)

    # Air
    def create_air(self, air: AirObject) -> AirObject:
        return self._create("AirObject", air, "air_objects")

    def replace_air(self, segment_id: str, air: AirObject) -> AirObject:
        return self._replace("air", "AirObject", segment_id, air, "air_objects")

    def delete_air(self, segment_id: str) -> None:
        self._delete("air", segment_id)

    # Lodging
    def create_lodging(self, lodging: LodgingObject) -> LodgingObject:
        return self._create("LodgingObject", lodging, "lodging_objects")

    def replace_lodging(self, lodging_id: str, lodging: LodgingObject) -> LodgingObject:
        return self._replace("lodging", "LodgingObject", lodging_id, lodging, "lodging_objects")

    def delete_lodging(self, lodging_id: str) -> None:
        self._delete("lodging", lodging_id)

    # Car
    def create_car(self, car: CarObject) -> CarObject:
        return self._create("CarObject", car, "car_objects")

    def replace_car(self, car_id: str, car: CarObject) -> CarObject:
        return self._replace("car", "CarObject", car_id, car, "car_objects")

    def delete_car(self, car_id: str) -> None:
        self._delete("car", car_id)

    # Rail
    def create_rail(self, rail: RailObject) -> RailObject:
        return self._create("RailObject", rail, "rail_objects")

    def replace_rail(self, rail_id: str, rail: RailObject) -> RailObject:
        return self._replace("rail", "RailObject", rail_id, rail, "rail_objects")

    def delete_rail(self, rail_id: str) -> None:
        self._delete("rail", rail_id)

    # Transport
    def create_transport(self, transport: TransportObject) -> TransportObject:
        return self._create("TransportObject", transport, "transport_objects")

    def replace_transport(self, transport_id: str, transport: TransportObject) -> TransportObject:
        return self._replace(
            "transport", "TransportObject", transport_id, transport, "transport_objects"
        )

    def delete_transport(self, transport_id: str) -> None:
        self._delete("transport", transport_id)

    # Cruise
    def create_cruise(self, cruise: CruiseObject) -> CruiseObject:
        return self._create("CruiseObject", cruise, "cruise_objects")

    def replace_cruise(self, cruise_id: str, cruise: CruiseObject) -> CruiseObject:
        return self._replace("cruise", "CruiseObject", cruise_id, cruise, "cruise_objects")

    def delete_cruise(self, cruise_id: str) -> None:
        self._delete("cruise", cruise_id)

    # Restaurant
    def create_restaurant(self, restaurant: RestaurantObject) -> RestaurantObject:
        return self._create("RestaurantObject", restaurant, "restaurant_objects")

    def replace_restaurant(
        self, restaurant_id: str, restaurant: RestaurantObject
    ) -> RestaurantObject:
        return self._replace(
            "restaurant",
            "RestaurantObject",
            restaurant_id,
            restaurant,
            "restaurant_objects",
        )

    def delete_restaurant(self, restaurant_id: str) -> None:
        self._delete("restaurant", restaurant_id)

    # Activity
    def create_activity(self, activity: ActivityObject) -> ActivityObject:
        return self._create("ActivityObject", activity, "activity_objects")

    def replace_activity(self, activity_id: str, activity: ActivityObject) -> ActivityObject:
        return self._replace(
            "activity", "ActivityObject", activity_id, activity, "activity_objects"
        )

    def delete_activity(self, activity_id: str) -> None:
        self._delete("activity", activity_id)

    # Note
    def create_note(self, note: NoteObject) -> NoteObject:
        return self._create("NoteObject", note, "note_objects")

    def replace_note(self, note_id: str, note: NoteObject) -> NoteObject:
        return self._replace("note", "NoteObject", note_id, note, "note_objects")

    def delete_note(self, note_id: str) -> None:
        self._delete("note", note_id)

    # Map
    def create_map(self, map_: MapObject) -> MapObject:
        return self._create("MapObject", map_, "map_objects")

    def replace_map(self, map_id: str, map_: MapObject) -> MapObject:
        return self._replace("map", "MapObject", map_id, map_, "map_objects")

    def delete_map(self, map_id: str) -> None:
        self._delete("map", map_id)

    # Directions
    def create_directions(self, directions: DirectionsObject) -> DirectionsObject:
        return self._create("DirectionsObject", directions, "directions_objects")

    def replace_directions(
        self, directions_id: str, directions: DirectionsObject
    ) -> DirectionsObject:
        return self._replace(
            "directions",
            "DirectionsObject",
            directions_id,
            directions,
            "directions_objects",
        )

    def delete_directions(self, directions_id: str) -> None:
        self._delete("directions", directions_id)

    # Parking
    def create_parking(self, parking: ParkingObject) -> ParkingObject:
        return self._create("ParkingObject", parking, "parking_objects")

    def replace_parking(self, parking_id: str, parking: ParkingObject) -> ParkingObject:
        return self._replace("parking", "ParkingObject", parking_id, parking, "parking_objects")

    def delete_parking(self, parking_id: str) -> None:
        self._delete("parking", parking_id)

    # CRS — partner-agency bulk operations
    def crs_load_reservations(self, xml_payload: str, *, company_key: str | None = None) -> Any:
        """Submit a CRS reservation payload (caller supplies pre-built XML).

        CRS loads are typically too large/specialised for a single typed
        wrapper. Accept the XML string the caller has already produced.
        Returns the raw Response envelope so callers can inspect any returned
        objects.
        """
        data: dict[str, str] = {"xml": xml_payload}
        if company_key is not None:
            data["company_key"] = company_key
        return self._transport.request_xml("POST", "/v1/crsLoadReservations", data=data)

    def crs_delete_reservations(self, record_locator: str) -> None:
        self._transport.request_xml(
            "POST",
            "/v1/crsDeleteReservations",
            data={"record_locator": record_locator},
        )

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
            envelope = self._transport.request_xml(
                "GET",
                "/v1/list/object",
                params={**base_params, "page_num": str(page)},
            )
            yield envelope
            max_page = envelope.max_page or 1
            if page >= max_page:
                return
            page += 1
