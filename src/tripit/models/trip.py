"""The Trip model and its read-only sub-structures."""

from __future__ import annotations

from datetime import date

from pydantic_xml import element

from tripit.models._base import TripItModel
from tripit.models.common import Address, Invitees, TripPurposes
from tripit.models.profile import Group


class TripStatus(TripItModel, tag="TripStatus"):
    status: str = element()


class TripStatuses(TripItModel, tag="TripStatuses"):
    trip_statuses: list[TripStatus] = element(tag="TripStatus", default_factory=list)


class TripCrsRemark(TripItModel, tag="TripCrsRemark"):
    record_locator: str = element()
    notes: str = element()


class TripCrsRemarks(TripItModel, tag="TripCrsRemarks"):
    trip_crs_remarks: list[TripCrsRemark] = element(tag="TripCrsRemark", default_factory=list)


class GroupInvitees(TripItModel, tag="GroupInvitees"):
    groups: list[Group] = element(tag="Group", default_factory=list)


class CrsTripDetails(TripItModel, tag="CrsTripDetails"):
    company_key: str | None = element(default=None)
    display_name: str | None = element(default=None)
    is_private: bool | None = element(default=None)
    trip_purposes: TripPurposes | None = element(tag="TripPurposes", default=None)


class Trip(TripItModel, tag="Trip"):
    """A TripIt trip."""

    trip_invitees: Invitees | None = element(tag="TripInvitees", default=None)
    trip_crs_remarks: TripCrsRemarks | None = element(tag="TripCrsRemarks", default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)
    relative_url: str | None = element(default=None)
    start_date: date | None = element(default=None)
    end_date: date | None = element(default=None)
    description: str | None = element(default=None)
    display_name: str | None = element(default=None)
    image_url: str | None = element(default=None)
    is_private: bool | None = element(default=None)
    primary_location: str | None = element(default=None)
    primary_location_address: Address | None = element(tag="PrimaryLocationAddress", default=None)
    is_expensible: bool | None = element(default=None)
    is_pro_enabled: bool | None = element(default=None)
    trip_purposes: TripPurposes | None = element(tag="TripPurposes", default=None)
    last_modified: int | None = element(default=None)
    group_invitees: GroupInvitees | None = element(tag="GroupInvitees", default=None)
    is_owner_traveler: bool | None = element(default=None)
    trip_statuses: TripStatuses | None = element(tag="TripStatuses", default=None)
