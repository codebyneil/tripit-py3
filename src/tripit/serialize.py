"""Pydantic-model → `<Request>` XML serializer for TripIt write endpoints.

TripIt's `/v1/create` and `/v1/replace/<entity>` accept a POST whose
`application/x-www-form-urlencoded` body has a single `xml` field whose value
is the marshalled XML payload conforming to `tripit-api-req-v1.xsd`. The
top-level element is always `<Request>` and it contains exactly one child
element naming the object type — e.g. `<Trip>...</Trip>`,
`<AirObject>...</AirObject>`.

We dump the pydantic model with `by_alias=True, exclude_none=True` so the
resulting dict mirrors the XSD element names (PascalCase for nested types,
snake_case for scalars). The dict is then walked recursively into `lxml`
Elements. Lists become repeated sibling elements.

Element ordering: most TripIt write types use `xs:all`, which is order-
agnostic on the wire. The `xs:sequence` types (`AirObject.Segment[]`,
`RailObject.Segment[]`, etc.) preserve dict insertion order naturally because
pydantic.model_dump emits fields in declaration order.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any

from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs
from pydantic import BaseModel


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, _dt.time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _build_children(parent: etree._Element, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                child = etree.SubElement(parent, key)
                if isinstance(item, dict):
                    _build_children(child, item)
                elif item is not None:
                    child.text = _stringify(item)
        elif isinstance(value, dict):
            child = etree.SubElement(parent, key)
            _build_children(child, value)
        else:
            child = etree.SubElement(parent, key)
            child.text = _stringify(value)


def model_to_request_xml(tag: str, model: BaseModel) -> str:
    """Serialize one pydantic model into a `<Request>` envelope.

    `tag` is the XSD element name for the object (`Trip`, `AirObject`, etc.).
    The returned string is ready to be sent as the `xml=` form field.
    """
    request = etree.Element("Request")
    inner = etree.SubElement(request, tag)
    data = model.model_dump(by_alias=True, exclude_none=True)
    _build_children(inner, data)
    return etree.tostring(
        request,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=None,
    ).decode("utf-8")
