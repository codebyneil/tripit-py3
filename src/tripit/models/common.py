"""Shared sub-models referenced by multiple TripIt object types.

Every field name and element/attribute binding mirrors `tripit-api-obj-v1.xsd`
verbatim. IDs are modelled as `str` (XML carries no numeric type and TripIt's
IDs are opaque); counts and timestamps that the XSD types as `xs:integer` are
`int`.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from pydantic_xml import attr, element

from tripit.models._base import TripItModel


class Address(TripItModel, tag="Address"):
    address: str | None = element(default=None)
    addr1: str | None = element(default=None)
    addr2: str | None = element(default=None)
    city: str | None = element(default=None)
    state: str | None = element(default=None)
    zip: str | None = element(default=None)
    country: str | None = element(default=None)
    latitude: Decimal | None = element(default=None)
    longitude: Decimal | None = element(default=None)


class DateTime(TripItModel, tag="DateTime"):
    date: _dt.date | None = element(default=None)
    time: _dt.time | None = element(default=None)
    timezone: str | None = element(default=None)
    is_timezone_manual: bool | None = element(default=None)
    utc_offset: str | None = element(default=None)
    preferred_timezone: str | None = element(default=None)


class ImageData(TripItModel, tag="ImageData"):
    content: str | None = element(default=None)
    mime_type: str | None = element(default=None)


class Image(TripItModel, tag="Image"):
    caption: str | None = element(default=None)
    url: str | None = element(default=None)
    image_data: ImageData | None = element(tag="ImageData", default=None)
    id: str | None = element(default=None)
    uuid: str | None = element(default=None)
    segment_id: str | None = element(default=None)
    segment_uuid: str | None = element(default=None)
    thumbnail_url: str | None = element(default=None)


class Creator(TripItModel, tag="Creator"):
    consumer_key: str | None = element(default=None)
    consumer_name: str | None = element(default=None)
    consumer_id: str | None = element(default=None)


class Traveler(TripItModel, tag="Traveler"):
    first_name: str | None = element(default=None)
    middle_name: str | None = element(default=None)
    last_name: str | None = element(default=None)
    frequent_traveler_num: str | None = element(default=None)
    frequent_traveler_supplier: str | None = element(default=None)
    meal_preference: str | None = element(default=None)
    seat_preference: str | None = element(default=None)
    ticket_num: str | None = element(default=None)


class Agency(TripItModel, tag="Agency"):
    agency_conf_num: str | None = element(default=None)
    agency_name: str | None = element(default=None)
    agency_client_name: str | None = element(default=None)
    agency_phone: str | None = element(default=None)
    agency_email_address: str | None = element(default=None)
    agency_url: str | None = element(default=None)
    agency_contact: str | None = element(default=None)
    partner_agency_id: str | None = element(default=None)


class PartnerAgency(TripItModel, tag="PartnerAgency"):
    partner_agency_id: str = element()
    partner_agency_name: str = element()
    partner_agency_short_name: str = element()
    partner_agency_logo_small_url: str | None = element(default=None)
    partner_agency_logo_medium_url: str | None = element(default=None)
    partner_agency_logo_large_url: str | None = element(default=None)


class CancelUserAction(TripItModel, tag="CancelUserAction"):
    action_code: str | None = element(default=None)
    action_at: int | None = element(default=None)
    action_by: str | None = element(default=None)


class Invitee(TripItModel, tag="Invitee"):
    profile_ref: str = attr()
    is_read_only: bool = element()
    is_traveler: bool = element()
    is_owner: bool | None = element(default=None)
    profile_ref_v2: str | None = element(default=None)
    inviter_profile_ref: str | None = element(default=None)


class Invitees(TripItModel, tag="Invitees"):
    invitees: list[Invitee] = element(tag="Invitee", default_factory=list)


class TripPurposes(TripItModel, tag="TripPurposes"):
    purpose_type_code: str = element()
    is_auto_generated: bool | None = element(default=None)
