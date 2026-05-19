"""TripIt client.

Phase 1 wires up `get_profile`, `get_trip`, and `list_trips`. Phase 2 fills in
the remaining `get_*` and `list_*` endpoints. Phase 3 adds the write surface.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal, Self

from tripit.auth import OAuth1Auth
from tripit.exceptions import TripItNotFoundError
from tripit.models.envelope import Response
from tripit.models.trip import Trip
from tripit.pagination import paginate
from tripit.transport import DEFAULT_API_URL, _Transport


class TripIt:
    """High-level TripIt v1 API client.

    Construct with OAuth 1.0a tokens. Use as a context manager to guarantee the
    underlying httpx.Client is closed.

    Example
    -------
    >>> with TripIt(
    ...     consumer_key="K", consumer_secret="S",
    ...     token="T", token_secret="TS",
    ... ) as client:
    ...     for trip in client.list_trips():
    ...         print(trip.id, trip.display_name)
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        token: str,
        token_secret: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float | None = 30.0,
        user_agent: str | None = None,
    ) -> None:
        auth = OAuth1Auth(
            consumer_key,
            consumer_secret,
            token=token,
            token_secret=token_secret,
        )
        self._transport = _Transport(
            auth,
            api_url=api_url,
            timeout=timeout,
            user_agent=user_agent,
        )

    @classmethod
    def two_legged(
        cls,
        consumer_key: str,
        consumer_secret: str,
        requestor_id: str,
        *,
        api_url: str = DEFAULT_API_URL,
        timeout: float | None = 30.0,
        user_agent: str | None = None,
    ) -> Self:
        """Construct a client using a 2-legged credential (no per-user token)."""
        instance = cls.__new__(cls)
        auth = OAuth1Auth(
            consumer_key,
            consumer_secret,
            requestor_id=requestor_id,
        )
        instance._transport = _Transport(
            auth,
            api_url=api_url,
            timeout=timeout,
            user_agent=user_agent,
        )
        return instance

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ----- Reads -----

    def get_trip(self, trip_id: str, *, include_objects: bool = False) -> Trip:
        """Fetch a single Trip by id. Raises `TripItNotFoundError` if missing."""
        params: dict[str, Any] = {"id": str(trip_id)}
        if include_objects:
            params["include_objects"] = "true"
        envelope = self._transport.request_json("GET", "/v1/get/trip", params=params)
        if not envelope.trips:
            raise TripItNotFoundError(f"Trip {trip_id} not in response", status_code=404)
        return envelope.trips[0]

    def list_trips(
        self,
        *,
        traveler: Literal["true", "false", "only"] | None = None,
        past: bool = False,
        modified_since: int | None = None,
        include_objects: bool = False,
        page_size: int = 25,
    ) -> Iterator[Trip]:
        """Yield all Trips matching the filter, paging transparently."""
        base_params: dict[str, Any] = {"page_size": str(page_size)}
        if traveler is not None:
            base_params["traveler"] = traveler
        if past:
            base_params["past"] = "true"
        if modified_since is not None:
            base_params["modified_since"] = str(modified_since)
        if include_objects:
            base_params["include_objects"] = "true"

        def fetch_page(page_num: int) -> Response:
            return self._transport.request_json(
                "GET",
                "/v1/list/trip",
                params={**base_params, "page_num": str(page_num)},
            )

        yield from paginate(fetch_page, lambda r: r.trips)
