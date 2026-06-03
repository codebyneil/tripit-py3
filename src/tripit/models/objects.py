"""All TripIt reservation/object types: air, lodging, car, rail, etc.

A small inheritance hierarchy mirroring the XSD:

- `BaseObject` — the XSD `Object` base (id, uuid, trip ids, Creator, Image[]).
- `BaseReservationObject(BaseObject)` — the XSD `ReservationObject` extension
  (booking/supplier fields, Agency, CancelUserAction). Parent of Air/Lodging/
  Car/Parking/Rail/Transport/Cruise/Restaurant/Activity.
- Plain objects (Note, Map, Directions, Weather) extend `BaseObject` directly.

Field order follows the XSD so serialized `<Request>` payloads validate against
the sequenced complex types.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from pydantic_xml import element

from tripit.models._base import TripItModel
from tripit.models.common import (
    Address,
    Agency,
    CancelUserAction,
    Creator,
    DateTime,
    Image,
    Traveler,
)
from tripit.models.seattracker import SeatTrackerSubscription


class BaseObject(TripItModel):
    """Fields shared by every TripIt object (the XSD `Object` type)."""

    id: str | None = element(default=None)
    uuid: str | None = element(default=None)
    trip_id: str | None = element(default=None)
    trip_uuid: str | None = element(default=None)
    is_client_traveler: bool | None = element(default=None)
    relative_url: str | None = element(default=None)
    display_name: str | None = element(default=None)
    images: list[Image] = element(tag="Image", default_factory=list)
    creator: Creator | None = element(tag="Creator", default=None)
    is_display_name_auto_generated: bool | None = element(default=None)
    last_modified: int | None = element(default=None)


class BaseReservationObject(BaseObject):
    """The XSD `ReservationObject` extension of `Object`."""

    cancel_user_action: CancelUserAction | None = element(tag="CancelUserAction", default=None)
    cancellation_date_time: DateTime | None = element(tag="CancellationDateTime", default=None)
    booking_date: _dt.date | None = element(default=None)
    booking_rate: str | None = element(default=None)
    booking_site_conf_num: str | None = element(default=None)
    booking_site_name: str | None = element(default=None)
    booking_site_phone: str | None = element(default=None)
    booking_site_email_address: str | None = element(default=None)
    booking_site_url: str | None = element(default=None)
    record_locator: str | None = element(default=None)
    supplier_conf_num: str | None = element(default=None)
    supplier_contact: str | None = element(default=None)
    supplier_email_address: str | None = element(default=None)
    supplier_name: str | None = element(default=None)
    supplier_phone: str | None = element(default=None)
    supplier_url: str | None = element(default=None)
    is_purchased: bool | None = element(default=None)
    notes: str | None = element(default=None)
    restrictions: str | None = element(default=None)
    total_cost: str | None = element(default=None)
    is_tripit_booking: bool | None = element(default=None)
    has_possible_cancellation: bool | None = element(default=None)
    agency: Agency | None = element(tag="Agency", default=None)


# ---------- Air ----------


class FlightStatus(TripItModel, tag="FlightStatus"):
    scheduled_departure_date_time: DateTime | None = element(
        tag="ScheduledDepartureDateTime", default=None
    )
    estimated_departure_date_time: DateTime | None = element(
        tag="EstimatedDepartureDateTime", default=None
    )
    scheduled_arrival_date_time: DateTime | None = element(
        tag="ScheduledArrivalDateTime", default=None
    )
    estimated_arrival_date_time: DateTime | None = element(
        tag="EstimatedArrivalDateTime", default=None
    )
    flight_status: str = element()
    is_connection_at_risk: bool | None = element(default=None)
    departure_terminal: str | None = element(default=None)
    departure_gate: str | None = element(default=None)
    arrival_terminal: str | None = element(default=None)
    arrival_gate: str | None = element(default=None)
    layover_minutes: str | None = element(default=None)
    baggage_claim: str | None = element(default=None)
    diverted_airport_code: str | None = element(default=None)
    last_modified: int = element()


class Emissions(TripItModel, tag="Emissions"):
    """TripIt extension on AirSegment — NOT in the published XSD.

    Confirmed emitted by the live API as ``<Emissions><co2>..</co2></Emissions>``.
    Modelled explicitly so strict parsing accepts it; `co2` is the only field
    observed so far.
    """

    co2: Decimal | None = element(default=None)


class AirSegment(TripItModel, tag="AirSegment"):
    status: FlightStatus | None = element(tag="Status", default=None)
    emissions: Emissions | None = element(tag="Emissions", default=None)
    seat_tracker_subscription: SeatTrackerSubscription | None = element(
        tag="SeatTrackerSubscription", default=None
    )
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    start_airport_code: str | None = element(default=None)
    start_airport_name: str | None = element(default=None)
    start_airport_latitude: Decimal | None = element(default=None)
    start_airport_longitude: Decimal | None = element(default=None)
    start_city_name: str | None = element(default=None)
    start_country_code: str | None = element(default=None)
    start_gate: str | None = element(default=None)
    start_terminal: str | None = element(default=None)
    end_airport_code: str | None = element(default=None)
    end_airport_name: str | None = element(default=None)
    end_airport_latitude: Decimal | None = element(default=None)
    end_airport_longitude: Decimal | None = element(default=None)
    end_city_name: str | None = element(default=None)
    end_country_code: str | None = element(default=None)
    end_gate: str | None = element(default=None)
    end_terminal: str | None = element(default=None)
    marketing_airline: str | None = element(default=None)
    marketing_airline_code: str | None = element(default=None)
    marketing_flight_number: str | None = element(default=None)
    operating_airline: str | None = element(default=None)
    operating_airline_code: str | None = element(default=None)
    operating_flight_number: str | None = element(default=None)
    alternate_flights_url: str | None = element(default=None)
    aircraft: str | None = element(default=None)
    aircraft_display_name: str | None = element(default=None)
    distance: str | None = element(default=None)
    duration: str | None = element(default=None)
    entertainment: str | None = element(default=None)
    meal: str | None = element(default=None)
    notes: str | None = element(default=None)
    ontime_perc: str | None = element(default=None)
    seats: str | None = element(default=None)
    service_class: str | None = element(default=None)
    stops: str | None = element(default=None)
    baggage_claim: str | None = element(default=None)
    check_in_url: str | None = element(default=None)
    mobile_check_in_url: str | None = element(default=None)
    refund_info_url: str | None = element(default=None)
    mobile_refund_info_url: str | None = element(default=None)
    change_reservation_url: str | None = element(default=None)
    mobile_change_reservation_url: str | None = element(default=None)
    customer_support_url: str | None = element(default=None)
    mobile_customer_support_url: str | None = element(default=None)
    general_fees_url: str | None = element(default=None)
    web_home_url: str | None = element(default=None)
    mobile_home_url: str | None = element(default=None)
    is_eligible_seattracker: bool | None = element(default=None)
    conflict_resolution_url: str | None = element(default=None)
    is_hidden: bool | None = element(default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)
    is_international: bool | None = element(default=None)
    does_cross_idl: bool | None = element(default=None)


class AirObject(BaseReservationObject, tag="AirObject"):
    segments: list[AirSegment] = element(tag="Segment", default_factory=list)
    travelers: list[Traveler] = element(tag="Traveler", default_factory=list)


# ---------- Lodging ----------


class LodgingObject(BaseReservationObject, tag="LodgingObject"):
    estimated_start_date_time: DateTime | None = element(tag="EstimatedStartDateTime", default=None)
    estimated_end_date_time: DateTime | None = element(tag="EstimatedEndDateTime", default=None)
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    address: Address | None = element(tag="Address", default=None)
    guests: list[Traveler] = element(tag="Guest", default_factory=list)
    number_guests: str | None = element(default=None)
    number_rooms: str | None = element(default=None)
    room_type: str | None = element(default=None)
    bic_code: str | None = element(default=None)


# ---------- Car ----------


class CarObject(BaseReservationObject, tag="CarObject"):
    estimated_start_date_time: DateTime | None = element(tag="EstimatedStartDateTime", default=None)
    estimated_end_date_time: DateTime | None = element(tag="EstimatedEndDateTime", default=None)
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    start_location_address: Address | None = element(tag="StartLocationAddress", default=None)
    end_location_address: Address | None = element(tag="EndLocationAddress", default=None)
    reservation_holder: Traveler | None = element(tag="ReservationHolder", default=None)
    drivers: list[Traveler] = element(tag="Driver", default_factory=list)
    start_location_hours: str | None = element(default=None)
    start_location_name: str | None = element(default=None)
    start_location_phone: str | None = element(default=None)
    end_location_hours: str | None = element(default=None)
    end_location_name: str | None = element(default=None)
    end_location_phone: str | None = element(default=None)
    car_description: str | None = element(default=None)
    car_type: str | None = element(default=None)
    mileage_charges: str | None = element(default=None)


# ---------- Parking ----------


class ParkingObject(BaseReservationObject, tag="ParkingObject"):
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    address: Address | None = element(tag="Address", default=None)
    location_hours: str | None = element(default=None)
    location_name: str | None = element(default=None)
    valet_ticket_num: str | None = element(default=None)
    location_phone: str | None = element(default=None)


# ---------- Rail ----------


class RailSegment(TripItModel, tag="RailSegment"):
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    start_station_address: Address | None = element(tag="StartStationAddress", default=None)
    end_station_address: Address | None = element(tag="EndStationAddress", default=None)
    start_station_name: str | None = element(default=None)
    end_station_name: str | None = element(default=None)
    carrier_name: str | None = element(default=None)
    coach_number: str | None = element(default=None)
    confirmation_num: str | None = element(default=None)
    seats: str | None = element(default=None)
    service_class: str | None = element(default=None)
    train_number: str | None = element(default=None)
    train_type: str | None = element(default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)


class RailObject(BaseReservationObject, tag="RailObject"):
    segments: list[RailSegment] = element(tag="Segment", default_factory=list)
    travelers: list[Traveler] = element(tag="Traveler", default_factory=list)


# ---------- Transport ----------


class TransportSegment(TripItModel, tag="TransportSegment"):
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    start_location_address: Address | None = element(tag="StartLocationAddress", default=None)
    end_location_address: Address | None = element(tag="EndLocationAddress", default=None)
    start_location_name: str | None = element(default=None)
    end_location_name: str | None = element(default=None)
    detail_type_code: str | None = element(default=None)
    carrier_name: str | None = element(default=None)
    confirmation_num: str | None = element(default=None)
    number_passengers: str | None = element(default=None)
    vehicle_description: str | None = element(default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)


class TransportObject(BaseReservationObject, tag="TransportObject"):
    segments: list[TransportSegment] = element(tag="Segment", default_factory=list)
    travelers: list[Traveler] = element(tag="Traveler", default_factory=list)


# ---------- Cruise ----------


class CruiseSegment(TripItModel, tag="CruiseSegment"):
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    location_address: Address | None = element(tag="LocationAddress", default=None)
    location_name: str | None = element(default=None)
    detail_type_code: str | None = element(default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)


class CruiseObject(BaseReservationObject, tag="CruiseObject"):
    segments: list[CruiseSegment] = element(tag="Segment", default_factory=list)
    travelers: list[Traveler] = element(tag="Traveler", default_factory=list)
    cabin_number: str | None = element(default=None)
    cabin_type: str | None = element(default=None)
    dining: str | None = element(default=None)
    ship_name: str | None = element(default=None)


# ---------- Restaurant ----------


class RestaurantObject(BaseReservationObject, tag="RestaurantObject"):
    date_time: DateTime | None = element(tag="DateTime", default=None)
    address: Address | None = element(tag="Address", default=None)
    reservation_holder: Traveler | None = element(tag="ReservationHolder", default=None)
    attendees: list[Traveler] = element(tag="Attendee", default_factory=list)
    cuisine: str | None = element(default=None)
    dress_code: str | None = element(default=None)
    hours: str | None = element(default=None)
    number_patrons: str | None = element(default=None)
    price_range: str | None = element(default=None)


# ---------- Activity ----------


class ActivityObject(BaseReservationObject, tag="ActivityObject"):
    start_date_time: DateTime | None = element(tag="StartDateTime", default=None)
    end_date_time: DateTime | None = element(tag="EndDateTime", default=None)
    end_time: _dt.time | None = element(default=None)
    address: Address | None = element(tag="Address", default=None)
    participants: list[Traveler] = element(tag="Participant", default_factory=list)
    detail_type_code: str | None = element(default=None)
    location_name: str | None = element(default=None)


# ---------- Plain objects (Note / Map / Directions / Weather) ----------


class NoteObject(BaseObject, tag="NoteObject"):
    date_time: DateTime | None = element(tag="DateTime", default=None)
    address: Address | None = element(tag="Address", default=None)
    detail_type_code: str | None = element(default=None)
    source: str | None = element(default=None)
    text: str | None = element(default=None)
    url: str | None = element(default=None)
    notes: str | None = element(default=None)


class MapObject(BaseObject, tag="MapObject"):
    date_time: DateTime | None = element(tag="DateTime", default=None)
    address: Address | None = element(tag="Address", default=None)


class DirectionsObject(BaseObject, tag="DirectionsObject"):
    date_time: DateTime | None = element(tag="DateTime", default=None)
    start_address: Address | None = element(tag="StartAddress", default=None)
    end_address: Address | None = element(tag="EndAddress", default=None)
    detail_type_code: str | None = element(default=None)


class WeatherObject(BaseObject, tag="WeatherObject"):
    date: _dt.date | None = element(default=None)
    location: str | None = element(default=None)
    avg_high_temp_c: float | None = element(default=None)
    avg_low_temp_c: float | None = element(default=None)
    avg_wind_speed_kn: float | None = element(default=None)
    avg_precipitation_cm: float | None = element(default=None)
    avg_snow_depth_cm: float | None = element(default=None)
