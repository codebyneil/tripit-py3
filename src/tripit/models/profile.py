"""Profile model and its many sub-types (all read-only in the TripIt API)."""

from __future__ import annotations

import datetime as _dt

from pydantic_xml import attr, element

from tripit.models._base import TripItModel
from tripit.models.common import DateTime


class ProfileEmailAddress(TripItModel, tag="ProfileEmailAddress"):
    uuid: str = element()
    uuid_ref: str = element()
    email_ref: str | None = element(default=None)
    address: str = element()
    is_auto_import: bool = element()
    is_confirmed: bool = element()
    is_primary: bool = element()
    is_auto_inbox_eligible: bool | None = element(default=None)
    import_trip_plan_sharing: str | None = element(default=None)
    last_auto_inbox_fetch_date_time: DateTime | None = element(
        tag="LastAutoInboxFetchDateTime", default=None
    )


class ProfileEmailAddresses(TripItModel, tag="ProfileEmailAddresses"):
    profile_email_addresses: list[ProfileEmailAddress] = element(
        tag="ProfileEmailAddress", default_factory=list
    )


class NotificationSetting(TripItModel, tag="NotificationSetting"):
    code: str = element()
    name: str = element()
    type: str = element()
    is_enabled: bool = element()
    # Despite the `is_` prefix, the XSD types this as a string (tier label).
    is_premium: str = element()


class NotificationSettings(TripItModel, tag="NotificationSettings"):
    settings: list[NotificationSetting] = element(tag="NotificationSetting", default_factory=list)


class Group(TripItModel, tag="Group"):
    display_name: str = element()
    url: str = element()
    unique_name: str = element()
    is_free: bool = element()


class GroupMemberships(TripItModel, tag="GroupMemberships"):
    groups: list[Group] = element(tag="Group", default_factory=list)


class AdditionalFactor(TripItModel, tag="AdditionalFactor"):
    type: str = element()
    display_name: str | None = element(default=None)


class AdditionalFactors(TripItModel, tag="AdditionalFactors"):
    factors: list[AdditionalFactor] = element(tag="AdditionalFactor", default_factory=list)


class AiImport(TripItModel, tag="AiImport"):
    is_opt_in_visible: bool | None = element(default=None)
    is_opt_in_read_only: bool | None = element(default=None)
    is_opted_in: bool | None = element(default=None)
    opted_in_ts: int | None = element(default=None)
    introduced_feature_mobile_ts: int | None = element(default=None)
    introduced_feature_webapp_ts: int | None = element(default=None)


class UserSettings(TripItModel, tag="UserSettings"):
    ai_import: AiImport | None = element(tag="AiImport", default=None)


class BillingPeriod(TripItModel, tag="BillingPeriod"):
    product_type_code: str = element()
    end_date: _dt.date = element()
    hard_end_date: _dt.date = element()


class BillingPeriods(TripItModel, tag="BillingPeriods"):
    periods: list[BillingPeriod] = element(tag="BillingPeriod", default_factory=list)


class Profile(TripItModel, tag="Profile"):
    """A TripIt user profile. `ref` is an XML attribute on the Profile element."""

    ref: str = attr()

    profile_email_addresses: ProfileEmailAddresses | None = element(
        tag="ProfileEmailAddresses", default=None
    )
    notification_settings: NotificationSettings | None = element(
        tag="NotificationSettings", default=None
    )
    group_memberships: GroupMemberships | None = element(tag="GroupMemberships", default=None)
    additional_factors: AdditionalFactors | None = element(tag="AdditionalFactors", default=None)
    user_settings: UserSettings | None = element(tag="UserSettings", default=None)
    billing_periods: BillingPeriods | None = element(tag="BillingPeriods", default=None)

    is_client: bool = element()
    is_pro: bool = element()
    screen_name: str = element()
    public_display_name: str = element()
    date_of_birth: _dt.date | None = element(default=None)
    profile_url: str = element()
    first_name: str | None = element(default=None)
    middle_name: str | None = element(default=None)
    last_name: str | None = element(default=None)
    home_city: str | None = element(default=None)
    home_country_code: str | None = element(default=None)
    home_airport: str | None = element(default=None)
    company: str | None = element(default=None)
    about_me_info: str | None = element(default=None)
    photo_url: str | None = element(default=None)
    activity_feed_url: str | None = element(default=None)
    alerts_feed_url: str | None = element(default=None)
    ical_url: str | None = element(default=None)
    cal_user_display_name: str | None = element(default=None)
    is_cal_detailed: bool | None = element(default=None)
    is_cal_localtime: bool | None = element(default=None)
    is_cal_including_notes: bool | None = element(default=None)
    is_cal_including_sensitive_info: bool | None = element(default=None)
    language_tag: str | None = element(default=None)
    date_endian_format: str | None = element(default=None)
    hour_clock: str | None = element(default=None)
    distance: str | None = element(default=None)
    temperature: str | None = element(default=None)
    should_auto_import: bool | None = element(default=None)
    sms_phone_number: str | None = element(default=None)
    sms_country_code: str | None = element(default=None)
    sms_email_address: str | None = element(default=None)
    should_allow_pro_purchase: bool | None = element(default=None)
    is_t4t_mobile_cal: bool | None = element(default=None)
    is_legacy_paid_app_user: bool | None = element(default=None)
    is_concur_linked: bool | None = element(default=None)
    uuid: str | None = element(default=None)
    jurisdiction: str | None = element(default=None)
    is_enterprise_pro: bool | None = element(default=None)
    risk_level: int | None = element(default=None)
    blocked_status: str | None = element(default=None)
    must_acknowledge_privacy_statement: bool | None = element(default=None)
    last_privacy_statement_acknowledgement: str | None = element(default=None)
    is_public_trip_sharing_disabled: bool | None = element(default=None)
    profile_ref_v2: str | None = element(default=None)
