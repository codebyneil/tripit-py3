"""Seat-tracker and aircraft-seat-map types (TripIt Pro flight data).

These hang off `AirSegment.SeatTrackerSubscription` in read responses. They are
data models only — the library exposes no write action to create a subscription
(see docs/README.md "Coverage & intentional exclusions").
"""

from __future__ import annotations

from pydantic_xml import element

from tripit.models._base import TripItModel
from tripit.models.common import DateTime


class SeatTrackerSearch(TripItModel, tag="SeatTrackerSearch"):
    departure_date_time: DateTime = element(tag="DepartureDateTime")
    arrival_date_time: DateTime | None = element(tag="ArrivalDateTime", default=None)
    last_search_date_time: DateTime | None = element(tag="LastSearchDateTime", default=None)
    last_updated_date_time: DateTime | None = element(tag="LastUpdatedDateTime", default=None)
    start_airport_code: str = element()
    end_airport_code: str = element()
    airline_code: str = element()
    flight_number: str = element()
    airline_phone_number: str | None = element(default=None)
    airline_url: str | None = element(default=None)
    deactivation_code: str | None = element(default=None)
    last_search_timestamp: int | None = element(default=None)
    last_updated_timestamp: int | None = element(default=None)
    id: str | None = element(default=None)


class SeatTrackerMatchedSeat(TripItModel, tag="matched_seats"):
    matched_seat: str | None = element(default=None)
    match_index: int | None = element(default=None)


class SeatTrackerSubscriptionMatches(TripItModel, tag="SeatTrackerSubscriptionMatches"):
    num_matches: int | None = element(default=None)
    matched_seats: list[SeatTrackerMatchedSeat] = element(tag="matched_seats", default_factory=list)
    last_updated_date_time: DateTime | None = element(tag="LastUpdatedDateTime", default=None)
    last_updated_timestamp: int | None = element(default=None)


class SeatPreferences(TripItModel, tag="seat_preferences"):
    seat_preference: list[str] = element(tag="seat_preference", default_factory=list)


class AreaPreferences(TripItModel, tag="area_preferences"):
    area_preference: list[str] = element(tag="area_preference", default_factory=list)


class SeatTrackerCriteria(TripItModel, tag="SeatTrackerCriteria"):
    qualifier: str | None = element(default=None)
    seat_preferences: list[SeatPreferences] = element(tag="seat_preferences", default_factory=list)
    area_preferences: list[AreaPreferences] = element(tag="area_preferences", default_factory=list)
    should_find_first_class: bool | None = element(default=None)
    should_find_premium_seats: bool | None = element(default=None)
    should_find_economy_seats: bool | None = element(default=None)
    should_find_exit_row: bool | None = element(default=None)
    should_find_bulkhead_row: bool | None = element(default=None)
    adjacent_seat_amount: int | None = element(default=None)
    individual_seat: str | None = element(default=None)


class SeatTrackerSubscription(TripItModel, tag="SeatTrackerSubscription"):
    seat_tracker_search: SeatTrackerSearch | None = element(tag="SeatTrackerSearch", default=None)
    seat_tracker_subscription_matches: SeatTrackerSubscriptionMatches | None = element(
        tag="SeatTrackerSubscriptionMatches", default=None
    )
    seat_tracker_criteria: SeatTrackerCriteria | None = element(
        tag="SeatTrackerCriteria", default=None
    )
    trip_item_id: str | None = element(default=None)
    trip_item_uuid: str | None = element(default=None)
    display_name: str | None = element(default=None)
    description: str | None = element(default=None)
    seats: str | None = element(default=None)
    deactivation_code: str | None = element(default=None)
    last_updated_timestamp: int | None = element(default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)


class ITAircraftSeatMapAttributes(TripItModel, tag="Attributes"):
    is_ahead_of_wing: bool | None = element(default=None)
    is_over_wing: bool | None = element(default=None)
    is_behind_wing: bool | None = element(default=None)
    is_exit_row: bool | None = element(default=None)
    is_aisle: bool | None = element(default=None)
    is_window: bool | None = element(default=None)
    is_bulkhead: bool | None = element(default=None)
    is_preferred: bool | None = element(default=None)
    is_restricted: bool | None = element(default=None)
    is_not_a_seat: bool | None = element(default=None)
    is_restricted_recline: bool | None = element(default=None)
    is_upper_deck: bool | None = element(default=None)
    is_first_class: bool | None = element(default=None)
    is_premium_class: bool | None = element(default=None)
    is_economy_class: bool | None = element(default=None)


class ITAircraftSeatMapSeat(TripItModel, tag="ITAircraftSeatMapSeat"):
    code: str = element()
    status: str | None = element(default=None)
    attributes: ITAircraftSeatMapAttributes | None = element(tag="Attributes", default=None)


class _ITAircraftSeatMapSeats(TripItModel, tag="ITAircraftSeatMapSeats"):
    seats: list[ITAircraftSeatMapSeat] = element(tag="ITAircraftSeatMapSeat", default_factory=list)


class ITAircraftSeatMapRow(TripItModel, tag="ITAircraftSeatMapRow"):
    number: int = element()
    attributes: ITAircraftSeatMapAttributes | None = element(tag="Attributes", default=None)
    seats_wrapper: _ITAircraftSeatMapSeats | None = element(
        tag="ITAircraftSeatMapSeats", default=None
    )


class _ITAircraftSeatMapRows(TripItModel, tag="ITAircraftSeatMapRows"):
    rows: list[ITAircraftSeatMapRow] = element(tag="ITAircraftSeatMapRow", default_factory=list)


class ITAircraftSeatMapSection(TripItModel, tag="ITAircraftSeatMapSection"):
    column_header: str = element()
    number: int = element()
    is_upper_deck: bool = element()
    rows_wrapper: _ITAircraftSeatMapRows | None = element(
        tag="ITAircraftSeatMapRows", default=None
    )


class _ITAircraftSeatMapSections(TripItModel, tag="ITAircraftSeatMapSections"):
    sections: list[ITAircraftSeatMapSection] = element(
        tag="ITAircraftSeatMapSection", default_factory=list
    )


class ITAircraftSeatMap(TripItModel, tag="ITAircraftSeatMap"):
    sections_wrapper: _ITAircraftSeatMapSections | None = element(
        tag="ITAircraftSeatMapSections", default=None
    )
