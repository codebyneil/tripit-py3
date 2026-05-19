"""Shared pydantic configuration and helper types used by every TripIt model."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _coerce_id(value: Any) -> Any:
    """TripIt returns big integers as JSON strings sometimes and numbers other times.

    Coerce both to `str` so callers never have to think about precision.
    `None` passes through unchanged.
    """
    if value is None:
        return None
    return str(value)


def _coerce_bool(value: Any) -> Any:
    """TripIt's JSON encoding of booleans is inconsistent: 'true'/'false', 1/0, true/false."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes"}:
            return True
        if v in {"false", "0", "no", ""}:
            return False
    if isinstance(value, int):
        return bool(value)
    return value


def _ensure_list(value: Any) -> Any:
    """Wrap a single object into a single-element list.

    TripIt's JSON inconsistently emits collections as a bare object when there's
    only one element (`"Trip": {...}`) and as a list otherwise (`"Trip": [...]`).
    Apply this in `mode="before"` validators on every list field that may shrink.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]


TripItId = Annotated[str, BeforeValidator(_coerce_id)]
"""All TripIt entity IDs are opaque strings, never integers."""

TripItBool = Annotated[bool, BeforeValidator(_coerce_bool)]
"""Booleans that may arrive as 'true'/'false' strings or 1/0 integers."""


class TripItModel(BaseModel):
    """Base for every TripIt response model.

    - `populate_by_name=True` lets callers pass either the alias (PascalCase from
      XSD) or the Python attribute name (snake_case).
    - `extra="ignore"` keeps us forward-compatible: if TripIt adds new fields,
      the library doesn't crash.
    - `str_strip_whitespace=True` because some TripIt text fields arrive with
      stray whitespace on either side.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=False,
    )
