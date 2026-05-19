"""Profile model and its many sub-types."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from pydantic import Field, field_validator, model_validator

from tripit.models._base import TripItBool, TripItId, TripItModel


def _wrap_in_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class ProfileEmailAddress(TripItModel):
    uuid: str
    uuid_ref: str
    email_ref: str | None = None
    address: str
    is_auto_import: TripItBool
    is_confirmed: TripItBool
    is_primary: TripItBool | None = None


class ProfileEmailAddresses(TripItModel):
    profile_email_addresses: list[ProfileEmailAddress] = Field(
        default_factory=list, alias="ProfileEmailAddress"
    )

    @field_validator("profile_email_addresses", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class NotificationSetting(TripItModel):
    setting_type: str | None = None
    setting_method: str | None = None
    is_enabled: TripItBool | None = None


class NotificationSettings(TripItModel):
    settings: list[NotificationSetting] = Field(default_factory=list, alias="NotificationSetting")

    @field_validator("settings", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class Group(TripItModel):
    id: TripItId | None = None
    display_name: str | None = None
    url: str | None = None


class GroupMemberships(TripItModel):
    groups: list[Group] = Field(default_factory=list, alias="Group")

    @field_validator("groups", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class AdditionalFactor(TripItModel):
    factor_type: str | None = None
    factor_value: str | None = None


class AdditionalFactors(TripItModel):
    factors: list[AdditionalFactor] = Field(default_factory=list, alias="AdditionalFactor")

    @field_validator("factors", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class UserSettings(TripItModel):
    """Free-form user settings — fields vary by account; tolerate anything."""

    model_config = TripItModel.model_config.copy()
    # Keep the freeform bag accessible to callers who really need it.
    extra_settings: dict[str, Any] | None = None


class BillingPeriod(TripItModel):
    start_date: _dt.date | None = None
    end_date: _dt.date | None = None
    plan_name: str | None = None
    is_active: TripItBool | None = None


class BillingPeriods(TripItModel):
    periods: list[BillingPeriod] = Field(default_factory=list, alias="BillingPeriod")

    @field_validator("periods", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)


class Profile(TripItModel):
    """A TripIt user profile."""

    # The XSD declares `ref` as an XML attribute on the Profile element. TripIt's
    # JSON encoding emits attributes as a nested `@attributes` dict like
    # `{"@attributes": {"ref": "..."}}`. A `model_validator` flattens that into
    # the plain `ref` field below before standard parsing runs.
    ref: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _lift_attributes_ref(cls, data: Any) -> Any:
        if isinstance(data, dict):
            attrs = data.get("@attributes")
            if isinstance(attrs, dict) and "ref" in attrs:
                # Don't mutate the caller's dict.
                merged = {k: v for k, v in data.items() if k != "@attributes"}
                merged.setdefault("ref", attrs["ref"])
                return merged
        return data

    profile_email_addresses: ProfileEmailAddresses | None = Field(
        default=None, alias="ProfileEmailAddresses"
    )
    notification_settings: NotificationSettings | None = Field(
        default=None, alias="NotificationSettings"
    )
    group_memberships: GroupMemberships | None = Field(default=None, alias="GroupMemberships")
    additional_factors: AdditionalFactors | None = Field(default=None, alias="AdditionalFactors")
    user_settings: UserSettings | None = Field(default=None, alias="UserSettings")
    billing_periods: BillingPeriods | None = Field(default=None, alias="BillingPeriods")

    is_client: TripItBool | None = None
    is_pro: TripItBool | None = None
    screen_name: str | None = None
    public_display_name: str | None = None
    date_of_birth: _dt.date | None = None
    profile_url: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    home_city: str | None = None
    home_country_code: str | None = None
    home_airport: str | None = None
    company: str | None = None
    about_me_info: str | None = None
    photo_url: str | None = None
    activity_feed_url: str | None = None
    alerts_feed_url: str | None = None
    ical_url: str | None = None
    cal_user_display_name: str | None = None
    is_cal_detailed: TripItBool | None = None
    is_cal_localtime: TripItBool | None = None
    is_cal_including_notes: TripItBool | None = None
    is_cal_including_sensitive_info: TripItBool | None = None
    language_tag: str | None = None
    date_endian_format: str | None = None
    hour_clock: str | None = None
    distance: str | None = None
    temperature: str | None = None
    should_auto_import: TripItBool | None = None
    sms_phone_number: str | None = None
    sms_country_code: str | None = None
    sms_email_address: str | None = None
    should_allow_pro_purchase: TripItBool | None = None
    is_t4t_mobile_cal: TripItBool | None = None
    is_legacy_paid_app_user: TripItBool | None = None
    is_concur_linked: TripItBool | None = None
    uuid: str | None = None
    jurisdiction: str | None = None
    is_enterprise_pro: TripItBool | None = None
    risk_level: int | None = None
    blocked_status: str | None = None
    must_acknowledge_privacy_statement: TripItBool | None = None
    last_privacy_statement_acknowledgement: str | None = None
    is_public_trip_sharing_disabled: TripItBool | None = None
    profile_ref_v2: str | None = None
