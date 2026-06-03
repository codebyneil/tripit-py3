"""Exercise every object get/create/replace/delete wrapper.

These wrappers are near-identical, which makes a wrong tag/pluck mapping
(copy-paste error) the likeliest bug — so verify each one hits the right
endpoint and returns the right type.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from tripit import TripIt
from tripit.models import (
    ActivityObject,
    AirObject,
    CarObject,
    CruiseObject,
    DirectionsObject,
    LodgingObject,
    MapObject,
    NoteObject,
    ParkingObject,
    RailObject,
    RestaurantObject,
    TransportObject,
)

# (entity path segment, XML element name, get-method name, expected type)
OBJECT_TYPES = [
    ("air", "AirObject", "get_air", AirObject),
    ("lodging", "LodgingObject", "get_lodging", LodgingObject),
    ("car", "CarObject", "get_car", CarObject),
    ("rail", "RailObject", "get_rail", RailObject),
    ("transport", "TransportObject", "get_transport", TransportObject),
    ("cruise", "CruiseObject", "get_cruise", CruiseObject),
    ("restaurant", "RestaurantObject", "get_restaurant", RestaurantObject),
    ("activity", "ActivityObject", "get_activity", ActivityObject),
    ("note", "NoteObject", "get_note", NoteObject),
    ("map", "MapObject", "get_map", MapObject),
    ("directions", "DirectionsObject", "get_directions", DirectionsObject),
    ("parking", "ParkingObject", "get_parking", ParkingObject),
]


def _client() -> TripIt:
    return TripIt(
        consumer_key="ck",
        consumer_secret="cs",
        token="t",
        token_secret="ts",
        api_url="https://api.tripit.example",
    )


def _envelope(element_name: str, body: str = "<id>900</id>") -> bytes:
    return (
        f"<Response><timestamp>1</timestamp><num_bytes>1</num_bytes>"
        f"<{element_name}>{body}</{element_name}></Response>"
    ).encode()


@pytest.mark.parametrize(("entity", "element", "method", "typ"), OBJECT_TYPES)
@respx.mock
def test_get_object_dispatches_to_right_endpoint_and_type(
    entity: str, element: str, method: str, typ: type
) -> None:
    route = respx.get(f"https://api.tripit.example/v1/get/{entity}/id/900").mock(
        return_value=httpx.Response(200, content=_envelope(element))
    )
    with _client() as c:
        result = getattr(c, method)("900")
    assert route.called
    assert isinstance(result, typ)
    assert result.id == "900"


@respx.mock
def test_create_replace_delete_cycle_for_lodging() -> None:
    created = respx.post("https://api.tripit.example/v1/create").mock(
        return_value=httpx.Response(200, content=_envelope("LodgingObject"))
    )
    replaced = respx.post("https://api.tripit.example/v1/replace/lodging/id/900").mock(
        return_value=httpx.Response(200, content=_envelope("LodgingObject"))
    )
    deleted = respx.get("https://api.tripit.example/v1/delete/lodging/id/900").mock(
        return_value=httpx.Response(
            200, content=b"<Response><timestamp>1</timestamp><num_bytes>1</num_bytes></Response>"
        )
    )
    with _client() as c:
        obj = c.create_lodging(LodgingObject(supplier_name="Hotel"))
        assert obj.id == "900"
        c.replace_lodging("900", LodgingObject(supplier_name="Hotel 2"))
        c.delete_lodging("900")
    assert created.called
    assert replaced.called
    assert deleted.called
