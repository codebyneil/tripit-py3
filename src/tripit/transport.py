"""HTTP transport: one chokepoint for retries, timeouts, and envelope unwrap.

Every request the client makes flows through `_Transport.request_xml`. That
method:

1. Performs the GET/POST via the shared `httpx.Client` (always `format=xml`).
2. Maps non-2xx responses into the typed exception hierarchy.
3. Parses the XML body into a `Response` model via pydantic-xml.
4. Raises if `Response.Error[]` is populated; logs `Response.Warning[]`.
5. Retries on rate-limit / 5xx / transient network errors via tenacity.

httpx network errors never leak past this module — they're always wrapped in
`TripItTransportError`.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs
from pydantic import ValidationError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from tripit._version import __version__
from tripit.auth import OAuth1Auth
from tripit.exceptions import (
    TripItAPIError,
    TripItAuthError,
    TripItHTTPError,
    TripItNotFoundError,
    TripItRateLimitError,
    TripItServerError,
    TripItTransportError,
    TripItValidationError,
)
from tripit.models.envelope import Response
from tripit.xml import validate_response_xml

logger = logging.getLogger("tripit")

DEFAULT_API_URL = "https://api.tripit.com"
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
DEFAULT_LIMITS = httpx.Limits(max_connections=10, max_keepalive_connections=5)


_RETRYABLE_EXCEPTIONS = (
    TripItRateLimitError,
    TripItServerError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class _Transport:
    """Owns the httpx.Client and provides a typed request_json method."""

    def __init__(
        self,
        auth: OAuth1Auth,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float | httpx.Timeout | None = None,
        limits: httpx.Limits | None = None,
        user_agent: str | None = None,
        validate_responses: bool = False,
    ) -> None:
        if isinstance(timeout, (int, float)):
            timeout = httpx.Timeout(timeout)
        self._validate_responses = validate_responses
        self._client = httpx.Client(
            base_url=api_url,
            auth=auth,
            timeout=timeout or DEFAULT_TIMEOUT,
            limits=limits or DEFAULT_LIMITS,
            headers={"User-Agent": user_agent or f"tripit-py/{__version__}"},
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> _Transport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def request_xml(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Response:
        """Issue a request, retry on transient failures, return a parsed Response."""

        @retry(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            wait=wait_exponential_jitter(initial=1.0, max=30.0),
            stop=stop_after_attempt(5),
            reraise=True,
        )
        def _do() -> Response:
            return self._request_once(method, path, params=params, data=data)

        try:
            return _do()
        except RetryError as exc:  # pragma: no cover — tenacity reraise=True
            inner = exc.last_attempt.exception()
            if inner is not None:
                raise inner from exc
            raise

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Issue a request and return the raw XML text without model parsing.

        Used by the fixture-capture script to retain the full wire payload
        (including any out-of-schema elements the strict parser would reject).
        Retries on the same transient failures as `request_xml` but skips
        envelope unwrapping.
        """

        @retry(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            wait=wait_exponential_jitter(initial=1.0, max=30.0),
            stop=stop_after_attempt(5),
            reraise=True,
        )
        def _do() -> str:
            return self._request_raw_once(method, path, params=params, data=data)

        try:
            return _do()
        except RetryError as exc:  # pragma: no cover
            inner = exc.last_attempt.exception()
            if inner is not None:
                raise inner from exc
            raise

    def _request_raw_once(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> str:
        merged = {**(params or {}), "format": "xml"}
        try:
            response = self._client.request(method, path, params=merged, data=data)
        except httpx.HTTPError as exc:
            if isinstance(exc, _RETRYABLE_EXCEPTIONS):
                raise
            raise TripItTransportError(
                f"{method} {path} failed: {exc.__class__.__name__}: {exc}"
            ) from exc

        self._raise_for_status(response)
        return response.text

    def _request_once(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> Response:
        # Always request XML.
        params = {**(params or {}), "format": "xml"}
        try:
            response = self._client.request(method, path, params=params, data=data)
        except httpx.HTTPError as exc:
            # ConnectError / ReadTimeout / RemoteProtocolError will be retried by the
            # outer @retry decorator (they're in _RETRYABLE_EXCEPTIONS). Anything else
            # gets wrapped and re-raised so it's catchable as TripItError.
            if isinstance(exc, _RETRYABLE_EXCEPTIONS):
                raise
            raise TripItTransportError(
                f"{method} {path} failed: {exc.__class__.__name__}: {exc}"
            ) from exc

        self._raise_for_status(response)
        return self._parse_envelope(response)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        retry_after = _parse_retry_after(response.headers.get("retry-after"))
        body = response.text
        if status == 401 or status == 403:
            raise TripItAuthError(
                f"HTTP {status}: authentication rejected",
                status_code=status,
                retry_after=retry_after,
                response_body=body,
            )
        if status == 404:
            raise TripItNotFoundError(
                f"HTTP {status}: not found",
                status_code=status,
                retry_after=retry_after,
                response_body=body,
            )
        if status == 429:
            raise TripItRateLimitError(
                f"HTTP {status}: rate limited",
                status_code=status,
                retry_after=retry_after,
                response_body=body,
            )
        if status >= 500:
            raise TripItServerError(
                f"HTTP {status}: server error",
                status_code=status,
                retry_after=retry_after,
                response_body=body,
            )
        raise TripItHTTPError(
            f"HTTP {status}: unexpected status",
            status_code=status,
            retry_after=retry_after,
            response_body=body,
        )

    def _parse_envelope(self, response: httpx.Response) -> Response:
        payload = response.content
        if self._validate_responses:
            validate_response_xml(payload)
        try:
            envelope = Response.from_xml(payload)
        except ValidationError as exc:
            raise TripItValidationError(str(exc)) from exc
        except etree.XMLSyntaxError as exc:
            raise TripItValidationError(
                f"response was not valid XML: {response.text[:200]!r}"
            ) from exc

        if envelope.warnings:
            for warning in envelope.warnings:
                logger.warning(
                    "tripit warning: %s (entity=%s, ts=%s)",
                    warning.description,
                    warning.entity_type,
                    warning.timestamp,
                )

        if envelope.errors:
            first = envelope.errors[0]
            raise TripItAPIError(
                first.description,
                api_code=first.code,
                entity_type=first.entity_type,
            )

        return envelope
