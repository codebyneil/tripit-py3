"""Typed exception hierarchy for the TripIt client.

All exceptions raised by this library inherit from `TripItError`. httpx network
errors are wrapped in `TripItTransportError` at the transport layer — they never
leak to callers untyped.
"""

from __future__ import annotations


class TripItError(Exception):
    """Base class for every exception raised by this library."""


class TripItTransportError(TripItError):
    """A network-level failure: DNS, TLS, connect, read, protocol.

    The original `httpx` exception is preserved on `__cause__`.
    """


class TripItHTTPError(TripItError):
    """A non-2xx HTTP response, or a 2xx response with `Response.Error[]`."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        response_body: str | None = None,
        api_code: int | None = None,
        entity_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.response_body = response_body
        self.api_code = api_code
        self.entity_type = entity_type


class TripItAuthError(TripItHTTPError):
    """401, 403, or OAuth signature rejected."""


class TripItNotFoundError(TripItHTTPError):
    """404."""


class TripItRateLimitError(TripItHTTPError):
    """429. Retryable. `retry_after` is in seconds."""


class TripItServerError(TripItHTTPError):
    """5xx. Retryable."""


class TripItAPIError(TripItHTTPError):
    """2xx/4xx response body contained a populated `Response.Error[]` list."""


class TripItValidationError(TripItError):
    """A pydantic ValidationError occurred while parsing a response.

    The original exception is on `__cause__`.
    """
