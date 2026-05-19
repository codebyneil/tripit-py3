"""The Trip model — the root container the TripIt v1 API hangs everything off."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field

from tripit.models._base import TripItBool, TripItId, TripItModel
from tripit.models.common import Address, Invitees, TripPurposes


class Trip(TripItModel):
    """A TripIt trip.

    Phase 1 carries the scalar fields and the most-used nested types
    (`PrimaryLocationAddress`, `TripPurposes`, `TripInvitees`). The remaining
    complex children (`TripCrsRemarks`, `GroupInvitees`, `TripStatuses`) are
    kept as untyped dicts for now and will be promoted to typed models in
    Phase 2.
    """

    id: TripItId | None = None
    uuid: str | None = None
    relative_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    display_name: str | None = None
    image_url: str | None = None
    is_private: TripItBool | None = None
    primary_location: str | None = None
    primary_location_address: Address | None = Field(default=None, alias="PrimaryLocationAddress")
    is_expensible: TripItBool | None = None
    is_pro_enabled: TripItBool | None = None
    last_modified: int | None = None
    is_owner_traveler: TripItBool | None = None

    trip_purposes: TripPurposes | None = Field(default=None, alias="TripPurposes")
    trip_invitees: Invitees | None = Field(default=None, alias="TripInvitees")

    # Promoted to typed models in Phase 2.
    trip_crs_remarks: dict[str, Any] | None = Field(default=None, alias="TripCrsRemarks")
    group_invitees: dict[str, Any] | None = Field(default=None, alias="GroupInvitees")
    trip_statuses: dict[str, Any] | None = Field(default=None, alias="TripStatuses")
