"""PointsProgram and its sub-types."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from pydantic import Field, field_validator

from tripit.models._base import TripItId, TripItModel


def _wrap_in_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class PointsProgramActivity(TripItModel):
    date: _dt.date | None = None
    description: str | None = None
    base: str | None = None
    bonus: str | None = None
    total: str | None = None


class PointsProgramExpiration(TripItModel):
    date: _dt.date | None = None
    amount: str | None = None


class PointsProgramSubAccount(TripItModel):
    name: str | None = None
    account_number: str | None = None
    balance: str | None = None


class PointsProgram(TripItModel):
    id: TripItId | None = None
    name: str | None = None
    account_number: str | None = None
    account_login: str | None = None
    balance: str | None = None
    elite_status: str | None = None
    elite_next_status: str | None = None
    elite_ytd_qualify: str | None = None
    elite_need_to_earn: str | None = None
    last_modified: int | None = None

    activities: list[PointsProgramActivity] = Field(
        default_factory=list, alias="PointsProgramActivity"
    )
    expirations: list[PointsProgramExpiration] = Field(
        default_factory=list, alias="PointsProgramExpiration"
    )
    sub_accounts: list[PointsProgramSubAccount] = Field(
        default_factory=list, alias="PointsProgramSubAccount"
    )

    @field_validator("activities", "expirations", "sub_accounts", mode="before")
    @classmethod
    def _wrap(cls, value: Any) -> Any:
        return _wrap_in_list(value)
