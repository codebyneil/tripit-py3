"""All TripIt reservation/object types: air, lodging, car, rail, etc.

Modelled as a small inheritance hierarchy mirroring the XSD:

- `BaseObject` — id, uuid, trip_id, display_name, Creator, Image[]
- `BaseReservationObject(BaseObject)` — adds booking/supplier fields, Agency,
  CancelUserAction. Parent of Air/Lodging/Car/Rail/Transport/Cruise/Restaurant/
  Activity/Parking.
- Plain objects (Note, Map, Directions, Weather) inherit `BaseObject` directly.

Sub-segment models (`AirSegment`, `RailSegment`, etc.) live alongside their
parent objects.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from tripit.models._base import TripItBool, TripItId, TripItModel
from tripit.models.common import Address, Creator, DateTime, Image, Traveler


def _wrap_in_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# ---------- Shared base & reservation-level fields ----------


class CancelUserAction(TripItModel):
    action_code: str | None = None
    action_at: int | None = None
    action_by: str | None = None


class Agency(TripItModel):
    agency_conf_num: str | None = None
    agency_name: str | None = None
    agency_client_name: str | None = None
    agency_phone: str | None = None
    agency_email_address: str | None = None
    agency_url: str | None = None
    agency_contact: str | None = None
    partner_agency_id: TripItId | None = None


class PartnerAgency(TripItModel):
    partner_agency_id: TripItId
    partner_agency_name: str
    partner_agency_short_name: str
    partner_agency_logo_small_url: str | None = None
    partner_agency_logo_medium_url: str | None = None
    partner_agency_logo_large_url: str | None = None


class BaseObject(TripItModel):
    """Fields shared by every TripIt object subclass (`Object` in the XSD)."""

    id: TripItId | None = None
    uuid: str | None = None
    trip_id: TripItId | None = None
    trip_uuid: str | None = None
    is_client_traveler: TripItBool | None = None
    relative_url: str | None = None
    display_name: str | None = None
    images: list[Image] = Field(default_factory=list, alias="Image")
    creator: Creator | None = Field(default=None, alias="Creator")
    is_display_name_auto_generated: TripItBool | None = None
    last_modified: int | None = None

    @field_validator("images", mode="before")
    @classmethod
    def _wrap_images(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class BaseReservationObject(BaseObject):
    """Fields shared by every reservation-style object (extends `Object` in XSD)."""

    cancel_user_action: CancelUserAction | None = Field(default=None, alias="CancelUserAction")
    cancellation_date_time: DateTime | None = Field(default=None, alias="CancellationDateTime")
    booking_date: _dt.date | None = None
    booking_rate: str | None = None
    booking_site_conf_num: str | None = None
    booking_site_name: str | None = None
    booking_site_phone: str | None = None
    booking_site_email_address: str | None = None
    booking_site_url: str | None = None
    record_locator: str | None = None
    supplier_conf_num: str | None = None
    supplier_contact: str | None = None
    supplier_email_address: str | None = None
    supplier_name: str | None = None
    supplier_phone: str | None = None
    supplier_url: str | None = None
    is_purchased: TripItBool | None = None
    notes: str | None = None
    restrictions: str | None = None
    total_cost: str | None = None
    is_tripit_booking: TripItBool | None = None
    has_possible_cancellation: TripItBool | None = None
    agency: Agency | None = Field(default=None, alias="Agency")


# ---------- Air ----------


class FlightStatus(TripItModel):
    scheduled_departure_date_time: DateTime | None = Field(
        default=None, alias="ScheduledDepartureDateTime"
    )
    estimated_departure_date_time: DateTime | None = Field(
        default=None, alias="EstimatedDepartureDateTime"
    )
    scheduled_arrival_date_time: DateTime | None = Field(
        default=None, alias="ScheduledArrivalDateTime"
    )
    estimated_arrival_date_time: DateTime | None = Field(
        default=None, alias="EstimatedArrivalDateTime"
    )
    flight_status: str
    is_connection_at_risk: TripItBool | None = None
    departure_terminal: str | None = None
    departure_gate: str | None = None
    arrival_terminal: str | None = None
    arrival_gate: str | None = None
    layover_minutes: str | None = None
    baggage_claim: str | None = None
    diverted_airport_code: str | None = None
    last_modified: int


class AirSegment(TripItModel):
    status: FlightStatus | None = Field(default=None, alias="Status")
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    start_airport_code: str | None = None
    start_airport_name: str | None = None
    start_airport_latitude: Decimal | None = None
    start_airport_longitude: Decimal | None = None
    start_city_name: str | None = None
    start_country_code: str | None = None
    start_gate: str | None = None
    start_terminal: str | None = None
    end_airport_code: str | None = None
    end_airport_name: str | None = None
    end_airport_latitude: Decimal | None = None
    end_airport_longitude: Decimal | None = None
    end_city_name: str | None = None
    end_country_code: str | None = None
    end_gate: str | None = None
    end_terminal: str | None = None
    marketing_airline: str | None = None
    marketing_airline_code: str | None = None
    marketing_flight_number: str | None = None
    operating_airline: str | None = None
    operating_airline_code: str | None = None
    operating_flight_number: str | None = None
    alternate_flights_url: str | None = None
    aircraft: str | None = None
    aircraft_display_name: str | None = None
    distance: str | None = None
    duration: str | None = None
    entertainment: str | None = None
    meal: str | None = None
    notes: str | None = None
    ontime_perc: str | None = None
    seats: str | None = None
    service_class: str | None = None
    stops: str | None = None
    baggage_claim: str | None = None
    check_in_url: str | None = None
    mobile_check_in_url: str | None = None
    refund_info_url: str | None = None
    mobile_refund_info_url: str | None = None
    change_reservation_url: str | None = None
    mobile_change_reservation_url: str | None = None
    customer_support_url: str | None = None
    mobile_customer_support_url: str | None = None
    general_fees_url: str | None = None
    web_home_url: str | None = None
    mobile_home_url: str | None = None
    is_eligible_seattracker: TripItBool | None = None
    conflict_resolution_url: str | None = None
    is_hidden: TripItBool | None = None
    id: TripItId | None = None
    uuid: str | None = None
    is_international: TripItBool | None = None
    does_cross_idl: TripItBool | None = None
    # CO2/emissions data (added by TripIt mid-2024). Shape isn't in the XSD;
    # tolerate any nested structure.
    emissions: dict[str, Any] | None = Field(default=None, alias="Emissions")


class AirObject(BaseReservationObject):
    segments: list[AirSegment] = Field(default_factory=list, alias="Segment")
    travelers: list[Traveler] = Field(default_factory=list, alias="Traveler")

    @field_validator("segments", "travelers", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Lodging ----------


class LodgingObject(BaseReservationObject):
    estimated_start_date_time: DateTime | None = Field(default=None, alias="EstimatedStartDateTime")
    estimated_end_date_time: DateTime | None = Field(default=None, alias="EstimatedEndDateTime")
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    address: Address | None = Field(default=None, alias="Address")
    guests: list[Traveler] = Field(default_factory=list, alias="Guest")
    number_guests: str | None = None
    number_rooms: str | None = None
    room_type: str | None = None
    bic_code: str | None = None

    @field_validator("guests", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Car ----------


class CarObject(BaseReservationObject):
    estimated_start_date_time: DateTime | None = Field(default=None, alias="EstimatedStartDateTime")
    estimated_end_date_time: DateTime | None = Field(default=None, alias="EstimatedEndDateTime")
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    start_location_address: Address | None = Field(default=None, alias="StartLocationAddress")
    end_location_address: Address | None = Field(default=None, alias="EndLocationAddress")
    reservation_holder: Traveler | None = Field(default=None, alias="ReservationHolder")
    drivers: list[Traveler] = Field(default_factory=list, alias="Driver")
    start_location_hours: str | None = None
    start_location_name: str | None = None
    start_location_phone: str | None = None
    end_location_hours: str | None = None
    end_location_name: str | None = None
    end_location_phone: str | None = None
    car_description: str | None = None
    car_type: str | None = None
    mileage_charges: str | None = None

    @field_validator("drivers", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Parking ----------


class ParkingObject(BaseReservationObject):
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    address: Address | None = Field(default=None, alias="Address")
    location_hours: str | None = None
    location_name: str | None = None
    valet_ticket_num: str | None = None
    location_phone: str | None = None


# ---------- Rail ----------


class RailSegment(TripItModel):
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    start_station_address: Address | None = Field(default=None, alias="StartStationAddress")
    end_station_address: Address | None = Field(default=None, alias="EndStationAddress")
    start_station_name: str | None = None
    end_station_name: str | None = None
    carrier_name: str | None = None
    coach_number: str | None = None
    confirmation_num: str | None = None
    seats: str | None = None
    service_class: str | None = None
    train_number: str | None = None
    train_type: str | None = None
    id: TripItId | None = None
    uuid: str | None = None


class RailObject(BaseReservationObject):
    segments: list[RailSegment] = Field(default_factory=list, alias="Segment")
    travelers: list[Traveler] = Field(default_factory=list, alias="Traveler")

    @field_validator("segments", "travelers", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Transport ----------


class TransportSegment(TripItModel):
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    start_location_address: Address | None = Field(default=None, alias="StartLocationAddress")
    end_location_address: Address | None = Field(default=None, alias="EndLocationAddress")
    start_location_name: str | None = None
    end_location_name: str | None = None
    detail_type_code: str | None = None
    carrier_name: str | None = None
    confirmation_num: str | None = None
    number_passengers: str | None = None
    vehicle_description: str | None = None
    id: TripItId | None = None
    uuid: str | None = None


class TransportObject(BaseReservationObject):
    segments: list[TransportSegment] = Field(default_factory=list, alias="Segment")
    travelers: list[Traveler] = Field(default_factory=list, alias="Traveler")

    @field_validator("segments", "travelers", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Cruise ----------


class CruiseSegment(TripItModel):
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    location_address: Address | None = Field(default=None, alias="LocationAddress")
    location_name: str | None = None
    detail_type_code: str | None = None
    id: TripItId | None = None
    uuid: str | None = None


class CruiseObject(BaseReservationObject):
    segments: list[CruiseSegment] = Field(default_factory=list, alias="Segment")
    travelers: list[Traveler] = Field(default_factory=list, alias="Traveler")
    cabin_number: str | None = None
    cabin_type: str | None = None
    dining: str | None = None
    ship_name: str | None = None

    @field_validator("segments", "travelers", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Restaurant ----------


class RestaurantObject(BaseReservationObject):
    date_time: DateTime | None = Field(default=None, alias="DateTime")
    address: Address | None = Field(default=None, alias="Address")
    reservation_holder: Traveler | None = Field(default=None, alias="ReservationHolder")
    attendees: list[Traveler] = Field(default_factory=list, alias="Attendee")
    cuisine: str | None = None
    dress_code: str | None = None
    hours: str | None = None
    number_patrons: str | None = None
    price_range: str | None = None

    @field_validator("attendees", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Activity ----------


class ActivityObject(BaseReservationObject):
    start_date_time: DateTime | None = Field(default=None, alias="StartDateTime")
    end_date_time: DateTime | None = Field(default=None, alias="EndDateTime")
    end_time: _dt.time | None = None
    address: Address | None = Field(default=None, alias="Address")
    participants: list[Traveler] = Field(default_factory=list, alias="Participant")
    detail_type_code: str | None = None
    location_name: str | None = None

    @field_validator("participants", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


# ---------- Plain objects (Note / Map / Directions / Weather) ----------


class NoteObject(BaseObject):
    date_time: DateTime | None = Field(default=None, alias="DateTime")
    address: Address | None = Field(default=None, alias="Address")
    detail_type_code: str | None = None
    source: str | None = None
    text: str | None = None
    url: str | None = None
    notes: str | None = None


class MapObject(BaseObject):
    date_time: DateTime | None = Field(default=None, alias="DateTime")
    address: Address | None = Field(default=None, alias="Address")


class DirectionsObject(BaseObject):
    date_time: DateTime | None = Field(default=None, alias="DateTime")
    start_address: Address | None = Field(default=None, alias="StartAddress")
    end_address: Address | None = Field(default=None, alias="EndAddress")
    detail_type_code: str | None = None


class WeatherObject(BaseObject):
    date: _dt.date | None = None
    location: str | None = None
    avg_high_temp_c: float | None = None
    avg_low_temp_c: float | None = None
    avg_wind_speed_kn: float | None = None
    avg_precipitation_cm: float | None = None
    avg_snow_depth_cm: float | None = None
