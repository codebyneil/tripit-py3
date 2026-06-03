"""PointsProgram and its read-only sub-types."""

from __future__ import annotations

import datetime as _dt

from pydantic_xml import element

from tripit.models._base import TripItModel


class PointsProgramActivity(TripItModel, tag="Activity"):
    date: _dt.date = element()
    description: str | None = element(default=None)
    base: str | None = element(default=None)
    bonus: str | None = element(default=None)
    total: str | None = element(default=None)


class PointsProgramExpiration(TripItModel, tag="Expiration"):
    date: _dt.date = element()
    amount: str | None = element(default=None)


class PointsProgramSubAccount(TripItModel, tag="SubAccount"):
    id: int = element()
    account_number: str | None = element(default=None)
    name: str | None = element(default=None)
    nickname: str | None = element(default=None)
    balance: str | None = element(default=None)


class PointsProgram(TripItModel, tag="PointsProgram"):
    id: str | None = element(default=None)
    name: str | None = element(default=None)
    account_number: str | None = element(default=None)
    account_login: str | None = element(default=None)
    balance: str | None = element(default=None)
    elite_status: str | None = element(default=None)
    elite_next_status: str | None = element(default=None)
    elite_ytd_qualify: str | None = element(default=None)
    elite_need_to_earn: str | None = element(default=None)
    last_modified: int | None = element(default=None)
    last_fetched: int | None = element(default=None)
    total_num_activities: int | None = element(default=None)
    total_num_expirations: int | None = element(default=None)
    error_message: str | None = element(default=None)
    nickname: str | None = element(default=None)
    last_fetch_account_state_code: int | None = element(default=None)
    account_state_code: int | None = element(default=None)
    is_dm_supported: bool | None = element(default=None)
    is_editable: bool | None = element(default=None)
    is_user_tracked: bool | None = element(default=None)
    is_supported: bool | None = element(default=None)
    unanswered_security_question_id: int | None = element(default=None)
    unanswered_security_question: str | None = element(default=None)
    lifetime_points: str | None = element(default=None)
    supplier_code: str | None = element(default=None)
    program_date: _dt.date | None = element(default=None)
    activities: list[PointsProgramActivity] = element(tag="Activity", default_factory=list)
    expirations: list[PointsProgramExpiration] = element(tag="Expiration", default_factory=list)
    sub_accounts: list[PointsProgramSubAccount] = element(tag="SubAccount", default_factory=list)
    url: str | None = element(default=None)
