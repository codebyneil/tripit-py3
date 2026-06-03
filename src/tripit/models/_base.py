"""Shared base model and config for every TripIt XML model.

The TripIt v1 API speaks XML (the three XSDs under `docs/` are the authoritative
contract). We bind directly to that wire format with `pydantic-xml`:

- `search_mode="unordered"` — TripIt's object types are `xs:all` (order-agnostic)
  and even the sequenced `Response` is parsed without relying on element order.
- `extra="forbid"` — the library is intentionally strict: any element or
  attribute that isn't in the XSD raises, so schema drift surfaces loudly rather
  than being silently dropped. (TripIt does emit a few out-of-schema fields,
  e.g. `Emissions`; those are catalogued as known deviations rather than
  absorbed — see docs/README.md.)
- Scalar coercion stays on (we do NOT use pydantic `strict=True`): XML leaves are
  text, and pydantic's lax mode turns `"true"`→bool, `"47.44"`→Decimal,
  `"2025-07-24"`→date, etc. Empty / self-closing elements (`<x/>`) coerce to
  `None`.

All entity IDs are opaque strings (XML carries no numeric type), so models use
plain `str` rather than any coercing alias.
"""

from __future__ import annotations

from pydantic import ConfigDict
from pydantic_xml import BaseXmlModel


class TripItModel(BaseXmlModel, search_mode="unordered"):
    """Base for every TripIt XML model. Strict, unordered, namespace-free."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=False,
    )
