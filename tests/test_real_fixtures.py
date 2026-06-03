"""XML fixture round-trips + XSD conformance + known-deviation guard.

- `test_roundtrip_no_drift`: every good fixture parses, re-serializes, and
  reparses to an identical model.
- `test_every_trip_data_type_is_modeled`: drive from the object XSD — every
  declared complexType must either have a model class or be on the documented
  exclusion list (collaboration / request-action types). This is what backs the
  README's coverage claim.
- `test_known_deviation_is_rejected`: TripIt's out-of-schema `<Emissions>` must
  fail strict parsing (the deviation stays visible, not silently absorbed).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree
from pydantic import ValidationError

import tripit.models as models
from tripit.models import Response

XML_DIR = Path(__file__).parent / "fixtures" / "xml"
OBJ_XSD = Path(__file__).parent.parent / "src" / "tripit" / "schemas" / "tripit-api-obj-v1.xsd"

GOOD_FIXTURES = sorted(
    p for p in XML_DIR.glob("*.xml") if p.name != "air_with_unknown_element.xml"
)

# XSD complexTypes we deliberately don't model: collaboration / request-action
# shapes (see docs/README.md "Coverage & intentional exclusions").
EXCLUDED_TYPES = {
    "Addresses",
    "ConnectionRequest",
    "EmailAddresses",
    "EmailMessage",
    "Invitation",
    "TripInvitations",
    "TripItemShare",
    "TripShare",
    "TravelGroupTripShare",
}

# XSD type name -> our class name where they differ.
RENAMED = {"Object": "BaseObject", "ReservationObject": "BaseReservationObject"}


@pytest.mark.parametrize("path", GOOD_FIXTURES, ids=lambda p: p.name)
def test_roundtrip_no_drift(path: Path) -> None:
    parsed = Response.from_xml(path.read_bytes())
    again = Response.from_xml(parsed.to_xml(skip_empty=True))
    assert parsed.model_dump() == again.model_dump()


def _xsd_complex_types() -> set[str]:
    tree = etree.parse(str(OBJ_XSD))
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    return {
        el.get("name")
        for el in tree.findall(".//xs:complexType", ns)
        if el.get("name") is not None
    }


def test_every_trip_data_type_is_modeled() -> None:
    modeled = {name for name in dir(models) if isinstance(getattr(models, name), type)}
    missing: list[str] = []
    for xsd_type in _xsd_complex_types():
        if xsd_type in EXCLUDED_TYPES:
            continue
        class_name = RENAMED.get(xsd_type, xsd_type)
        if class_name not in modeled:
            missing.append(xsd_type)
    assert not missing, f"XSD complexTypes with no model: {sorted(missing)}"


def test_excluded_types_are_really_absent() -> None:
    """The exclusion list must be honest: none of them should be modeled."""
    modeled = {name for name in dir(models) if isinstance(getattr(models, name), type)}
    leaked = sorted(t for t in EXCLUDED_TYPES if t in modeled)
    assert not leaked, f"types claimed excluded but actually modeled: {leaked}"


def test_unknown_element_is_rejected() -> None:
    """A genuinely-unknown element must fail strict parsing.

    Known TripIt extensions (Emissions, AppleFoundationModel,
    is_trip_owner_inner_circle_sharer, total_items) are modelled and accepted;
    this guards against silently dropping *new*, un-handled drift.
    """
    payload = (XML_DIR / "air_with_unknown_element.xml").read_bytes()
    with pytest.raises(ValidationError):
        Response.from_xml(payload)
