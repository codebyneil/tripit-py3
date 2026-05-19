"""Validate every captured `real_*.json` fixture parses and round-trips cleanly.

Two parametrized tests, run once per fixture file:

1. `test_roundtrip_no_drift`: parse → dump → parse → dump. The second-pass
   dump must equal the first-pass dump. Catches parser drift (e.g. a
   validator that mutates inputs, missing aliases, type coercion bugs).

2. `test_no_unmodeled_fields`: walk the raw JSON side-by-side with the parsed
   pydantic tree and surface any field TripIt sends that the model dropped
   via `extra="ignore"`. This is the high-signal model-coverage test —
   anything reported here is a hole in the typed surface.

The walker recurses into matched fields where the model declares a nested
`BaseModel` (or `list[BaseModel]`), so unmodeled fields deep inside Trip,
AirObject, etc. surface with a precise JSONPath.
"""

from __future__ import annotations

import json
import typing
from pathlib import Path
from types import UnionType
from typing import Any, get_args, get_origin

import pytest
from pydantic import BaseModel

from tripit.models.envelope import Response

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "json"

# All checked-in fixtures (both hand-curated and real captures).
ALL_FIXTURES = sorted(FIXTURES_DIR.glob("*.json"))


def _load_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text())
    # Capture script writes the wrapping {"Response": ...}; the hand-curated
    # fixtures use the same shape.
    return raw["Response"] if isinstance(raw, dict) and "Response" in raw else raw


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: p.name)
def test_roundtrip_no_drift(path: Path) -> None:
    """Parse → dump → parse → dump; the second pass must equal the first."""
    payload = _load_payload(path)
    parsed = Response.model_validate(payload)
    first = parsed.model_dump(by_alias=True, exclude_none=True, mode="json")
    second = Response.model_validate(first).model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    assert first == second


# ---------- Unknown-fields walker ----------


def _model_known_keys(model_cls: type[BaseModel]) -> set[str]:
    """Set of JSON keys a model would consume — alias if set, else field name."""
    keys: set[str] = set()
    for name, info in model_cls.model_fields.items():
        keys.add(info.alias or name)
        keys.add(name)
    return keys


def _resolve_model_type(annotation: Any) -> type[BaseModel] | None:
    """If `annotation` is BaseModel or list[BaseModel] (or Optional thereof),
    return the underlying BaseModel class. Otherwise None.
    """
    if annotation is None or annotation is type(None):
        return None
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation
        return None
    if origin is typing.Union or origin is UnionType:
        for arg in get_args(annotation):
            inner = _resolve_model_type(arg)
            if inner is not None:
                return inner
        return None
    if origin is list:
        args = get_args(annotation)
        if args:
            return _resolve_model_type(args[0])
    return None


def _walk_diff(
    raw: Any,
    model_obj: Any,
    *,
    path: str,
    errors: list[str],
) -> None:
    """Recursively compare raw JSON to a parsed model; collect unmodeled keys."""
    if model_obj is None or raw is None:
        return

    if isinstance(model_obj, BaseModel):
        if not isinstance(raw, dict):
            return
        known = _model_known_keys(type(model_obj))
        for raw_key, raw_value in raw.items():
            if raw_key not in known:
                errors.append(f"{path}.{raw_key}: unmodeled field on {type(model_obj).__name__}")
                continue
            # Recurse if this field has a model-typed sub-tree.
            info = type(model_obj).model_fields.get(raw_key) or next(
                (f for n, f in type(model_obj).model_fields.items() if (f.alias or n) == raw_key),
                None,
            )
            if info is None:
                continue
            inner_cls = _resolve_model_type(info.annotation)
            if inner_cls is None:
                continue
            # Find the parsed attribute name and value.
            python_attr: str | None = None
            for n, f in type(model_obj).model_fields.items():
                if (f.alias or n) == raw_key or n == raw_key:
                    python_attr = n
                    break
            if python_attr is None:
                continue
            parsed_value = getattr(model_obj, python_attr, None)
            _walk_diff(raw_value, parsed_value, path=f"{path}.{raw_key}", errors=errors)
        return

    if isinstance(model_obj, list):
        if not isinstance(raw, list):
            # Single-vs-list coercion happened on the parser side; treat as 1-elem.
            raw = [raw]
        for i, (raw_item, parsed_item) in enumerate(zip(raw, model_obj, strict=False)):
            _walk_diff(raw_item, parsed_item, path=f"{path}[{i}]", errors=errors)


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: p.name)
def test_no_unmodeled_fields(path: Path) -> None:
    """Every key TripIt emits should map to a declared field on our models."""
    payload = _load_payload(path)
    envelope = Response.model_validate(payload)
    errors: list[str] = []
    _walk_diff(payload, envelope, path="Response", errors=errors)
    if errors:
        msg = "\n".join(["Unmodeled fields detected:", *errors])
        pytest.fail(msg)
