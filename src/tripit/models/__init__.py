"""Pydantic models mirroring the TripIt v1 API data model.

All response objects, the wrapping `Response` envelope, and the error/warning
sub-objects live under this package. Field names follow Python snake_case;
PascalCase XSD nested types are reached via `Field(alias="XsdName")`.
"""

from tripit.models.common import (
    Address,
    Creator,
    DateTime,
    Image,
    ImageData,
    Traveler,
)
from tripit.models.envelope import Error, Response, Warning
from tripit.models.trip import Trip

__all__ = [
    "Address",
    "Creator",
    "DateTime",
    "Error",
    "Image",
    "ImageData",
    "Response",
    "Traveler",
    "Trip",
    "Warning",
]
