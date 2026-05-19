"""The top-level Response envelope returned by every TripIt v1 endpoint.

Every read returns a `Response` whose body holds zero or more typed object
collections plus optional `Error[]` / `Warning[]`. Pagination fields are
present on multi-page lists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from tripit.models._base import TripItModel
from tripit.models.trip import Trip


class Error(TripItModel):
    """Per-entity error from a partially-successful request, or a hard failure."""

    code: int
    detailed_error_code: float | None = None
    description: str
    entity_type: str
    timestamp: datetime


class Warning(TripItModel):
    """Per-entity warning that didn't block the response."""

    description: str
    entity_type: str
    timestamp: datetime


class Response(TripItModel):
    """Top-level wrapper for every TripIt API JSON response."""

    timestamp: int | None = None
    num_bytes: int | None = None
    errors: list[Error] = Field(default_factory=list, alias="Error")
    warnings: list[Warning] = Field(default_factory=list, alias="Warning")
    trips: list[Trip] = Field(default_factory=list, alias="Trip")
    profiles: list[dict[str, Any]] = Field(default_factory=list, alias="Profile")
    points_programs: list[dict[str, Any]] = Field(default_factory=list, alias="PointsProgram")
    air_objects: list[dict[str, Any]] = Field(default_factory=list, alias="AirObject")
    lodging_objects: list[dict[str, Any]] = Field(default_factory=list, alias="LodgingObject")
    car_objects: list[dict[str, Any]] = Field(default_factory=list, alias="CarObject")
    rail_objects: list[dict[str, Any]] = Field(default_factory=list, alias="RailObject")
    transport_objects: list[dict[str, Any]] = Field(default_factory=list, alias="TransportObject")
    cruise_objects: list[dict[str, Any]] = Field(default_factory=list, alias="CruiseObject")
    restaurant_objects: list[dict[str, Any]] = Field(default_factory=list, alias="RestaurantObject")
    activity_objects: list[dict[str, Any]] = Field(default_factory=list, alias="ActivityObject")
    note_objects: list[dict[str, Any]] = Field(default_factory=list, alias="NoteObject")
    map_objects: list[dict[str, Any]] = Field(default_factory=list, alias="MapObject")
    directions_objects: list[dict[str, Any]] = Field(default_factory=list, alias="DirectionsObject")
    parking_objects: list[dict[str, Any]] = Field(default_factory=list, alias="ParkingObject")
    weather_objects: list[dict[str, Any]] = Field(default_factory=list, alias="WeatherObject")
    partner_agencies: list[dict[str, Any]] = Field(default_factory=list, alias="PartnerAgency")

    page_num: int | None = None
    page_size: int | None = None
    max_page: int | None = None

    @field_validator(
        "errors",
        "warnings",
        "trips",
        "profiles",
        "points_programs",
        "air_objects",
        "lodging_objects",
        "car_objects",
        "rail_objects",
        "transport_objects",
        "cruise_objects",
        "restaurant_objects",
        "activity_objects",
        "note_objects",
        "map_objects",
        "directions_objects",
        "parking_objects",
        "weather_objects",
        "partner_agencies",
        mode="before",
    )
    @classmethod
    def _wrap_single(cls, value: Any) -> Any:
        """TripIt sometimes returns a bare object instead of a single-element list."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
