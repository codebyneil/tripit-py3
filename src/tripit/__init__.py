"""TripIt v1 API client — modern Python 3 rewrite."""

from tripit._version import __version__
from tripit.client import TripIt
from tripit.exceptions import (
    TripItAPIError,
    TripItAuthError,
    TripItError,
    TripItHTTPError,
    TripItNotFoundError,
    TripItRateLimitError,
    TripItServerError,
    TripItTransportError,
    TripItValidationError,
)
from tripit.models.common import Address, DateTime, Image, Traveler
from tripit.models.envelope import Error, Response, Warning
from tripit.models.trip import Trip

__all__ = [
    "Address",
    "DateTime",
    "Error",
    "Image",
    "Response",
    "Traveler",
    "Trip",
    "TripIt",
    "TripItAPIError",
    "TripItAuthError",
    "TripItError",
    "TripItHTTPError",
    "TripItNotFoundError",
    "TripItRateLimitError",
    "TripItServerError",
    "TripItTransportError",
    "TripItValidationError",
    "Warning",
    "__version__",
]
