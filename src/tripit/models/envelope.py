"""The top-level Response envelope returned by every TripIt v1 endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic_xml import element

from tripit.models._base import TripItModel
from tripit.models.common import PartnerAgency
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
    WeatherObject,
)
from tripit.models.points import PointsProgram
from tripit.models.profile import Profile
from tripit.models.trip import Trip


class Error(TripItModel, tag="Error"):
    code: int = element()
    detailed_error_code: Decimal | None = element(default=None)
    description: str = element()
    entity_type: str = element()
    timestamp: datetime = element()


class Warning(TripItModel, tag="Warning"):
    description: str = element()
    entity_type: str = element()
    timestamp: datetime = element()


class Response(TripItModel, tag="Response"):
    """Top-level wrapper for every TripIt API XML response."""

    timestamp: int = element()
    num_bytes: int = element()
    errors: list[Error] = element(tag="Error", default_factory=list)
    warnings: list[Warning] = element(tag="Warning", default_factory=list)

    trips: list[Trip] = element(tag="Trip", default_factory=list)
    activity_objects: list[ActivityObject] = element(tag="ActivityObject", default_factory=list)
    air_objects: list[AirObject] = element(tag="AirObject", default_factory=list)
    car_objects: list[CarObject] = element(tag="CarObject", default_factory=list)
    cruise_objects: list[CruiseObject] = element(tag="CruiseObject", default_factory=list)
    directions_objects: list[DirectionsObject] = element(
        tag="DirectionsObject", default_factory=list
    )
    lodging_objects: list[LodgingObject] = element(tag="LodgingObject", default_factory=list)
    map_objects: list[MapObject] = element(tag="MapObject", default_factory=list)
    note_objects: list[NoteObject] = element(tag="NoteObject", default_factory=list)
    parking_objects: list[ParkingObject] = element(tag="ParkingObject", default_factory=list)
    rail_objects: list[RailObject] = element(tag="RailObject", default_factory=list)
    restaurant_objects: list[RestaurantObject] = element(
        tag="RestaurantObject", default_factory=list
    )
    transport_objects: list[TransportObject] = element(tag="TransportObject", default_factory=list)
    weather_objects: list[WeatherObject] = element(tag="WeatherObject", default_factory=list)
    partner_agencies: list[PartnerAgency] = element(tag="PartnerAgency", default_factory=list)
    points_programs: list[PointsProgram] = element(tag="PointsProgram", default_factory=list)
    profiles: list[Profile] = element(tag="Profile", default_factory=list)

    page_num: int | None = element(default=None)
    page_size: int | None = element(default=None)
    max_page: int | None = element(default=None)
