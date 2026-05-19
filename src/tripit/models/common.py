"""Shared sub-models referenced by multiple TripIt object types."""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from tripit.models._base import TripItBool, TripItId, TripItModel


class Address(TripItModel):
    """A street address. TripIt uses this for trip locations and reservation venues."""

    address: str | None = None
    addr1: str | None = None
    addr2: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class DateTime(TripItModel):
    """A date+time pair with optional timezone — TripIt's primary temporal type."""

    date: _dt.date | None = None
    time: _dt.time | None = None
    timezone: str | None = None
    is_timezone_manual: TripItBool | None = None
    utc_offset: str | None = None


class ImageData(TripItModel):
    """Inline image payload used during create flows."""

    type: str | None = None
    name: str | None = None
    data: str | None = None


class Image(TripItModel):
    """A reference to an image hosted by TripIt (or in-flight image data on create)."""

    id: TripItId | None = None
    caption: str | None = None
    url: str | None = None
    secure_url: str | None = None
    image_data: ImageData | None = Field(default=None, alias="ImageData")


class Creator(TripItModel):
    """Who created an object (consumer app key + user)."""

    consumer_key: str | None = None
    user_id: TripItId | None = None
    display_name: str | None = None
    relative_url: str | None = None


class Traveler(TripItModel):
    """A person on a trip — sub-traveler of an air/rail/etc reservation."""

    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    frequent_traveler_num: str | None = None
    frequent_traveler_supplier: str | None = None
    meal_preference: str | None = None
    seat_preference: str | None = None
    ticket_num: str | None = None


class Invitee(TripItModel):
    """A user invited to view a trip or object."""

    is_read_only: TripItBool | None = None
    is_traveler: TripItBool | None = None
    is_sent: TripItBool | None = None
    is_owner: TripItBool | None = None
    profile_ref: str | None = None
    # Explicit field so the unknown-fields detector recognizes @attributes
    # as consumed by us; excluded from dumps so round-trip stays stable.
    attributes: dict[str, Any] | None = Field(default=None, alias="@attributes", exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _lift_profile_ref(cls, data: Any) -> Any:
        # TripIt's JSON encodes XML attributes (`profile_ref` on <Invitee>)
        # under an "@attributes" dict. Lift it into the flat field.
        if isinstance(data, dict):
            attrs = data.get("@attributes")
            if isinstance(attrs, dict) and "profile_ref" in attrs:
                merged = {**data}
                merged.setdefault("profile_ref", attrs["profile_ref"])
                return merged
        return data


class TripPurpose(TripItModel):
    """A tagged purpose for a trip (business, leisure, ...)."""

    id: TripItId | None = None
    purpose_name: str | None = None
    is_auto_generated: TripItBool | None = None


class TripPurposes(TripItModel):
    """Container for one or more `TripPurpose` entries.

    TripIt's JSON sometimes flattens a single TripPurpose into the wrapper,
    so the wrapper itself can carry `is_auto_generated` and `purpose_type_code`
    directly alongside the `TripPurpose` collection.
    """

    trip_purposes: list[TripPurpose] = Field(default_factory=list, alias="TripPurpose")
    is_auto_generated: TripItBool | None = None
    purpose_type_code: str | None = None

    @field_validator("trip_purposes", mode="before")
    @classmethod
    def _wrap_single(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class Invitees(TripItModel):
    """Container for trip/object invitees."""

    invitees: list[Invitee] = Field(default_factory=list, alias="Invitee")

    @field_validator("invitees", mode="before")
    @classmethod
    def _wrap_single(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
