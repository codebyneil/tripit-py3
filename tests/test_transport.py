"""Transport-layer tests: status mapping, retries, envelope unwrap, error/warning surfacing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import tenacity

from tripit.auth import OAuth1Auth
from tripit.exceptions import (
    TripItAPIError,
    TripItAuthError,
    TripItNotFoundError,
    TripItRateLimitError,
    TripItServerError,
    TripItTransportError,
    TripItValidationError,
)
from tripit.transport import _Transport

FIXTURES = Path(__file__).parent / "fixtures" / "json"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _no_sleep_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make tenacity not actually sleep between retries."""
    monkeypatch.setattr(tenacity.nap.time, "sleep", lambda _s: None)


def _auth() -> OAuth1Auth:
    return OAuth1Auth(
        "ck",
        "cs",
        token="t",
        token_secret="ts",
        _nonce="n",
        _timestamp=1,
    )


def _transport() -> _Transport:
    return _Transport(_auth(), api_url="https://api.tripit.example")


@respx.mock
def test_request_json_returns_response_envelope() -> None:
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, json=_load("list_trip_single_page.json"))
    )
    with _transport() as t:
        envelope = t.request_json("GET", "/v1/list/trip")
    assert len(envelope.trips) == 2


@respx.mock
def test_401_raises_auth_error() -> None:
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(401, text="bad signature")
    )
    with _transport() as t, pytest.raises(TripItAuthError) as exc_info:
        t.request_json("GET", "/v1/list/trip")
    assert exc_info.value.status_code == 401


@respx.mock
def test_404_raises_not_found() -> None:
    respx.get("https://api.tripit.example/v1/get/trip").mock(
        return_value=httpx.Response(404, text="no")
    )
    with _transport() as t, pytest.raises(TripItNotFoundError):
        t.request_json("GET", "/v1/get/trip")


@respx.mock
def test_429_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep_retry(monkeypatch)
    route = respx.get("https://api.tripit.example/v1/list/trip")
    route.side_effect = [
        httpx.Response(429, headers={"retry-after": "1"}, text="slow down"),
        httpx.Response(429, headers={"retry-after": "1"}, text="slow down"),
        httpx.Response(200, json=_load("list_trip_single_page.json")),
    ]
    with _transport() as t:
        envelope = t.request_json("GET", "/v1/list/trip")
    assert len(envelope.trips) == 2
    assert route.call_count == 3


@respx.mock
def test_429_gives_up_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep_retry(monkeypatch)
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(429, headers={"retry-after": "1"}, text="slow"),
    )
    with _transport() as t, pytest.raises(TripItRateLimitError):
        t.request_json("GET", "/v1/list/trip")


@respx.mock
def test_500_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep_retry(monkeypatch)
    route = respx.get("https://api.tripit.example/v1/list/trip")
    route.side_effect = [
        httpx.Response(500, text="oh no"),
        httpx.Response(200, json=_load("list_trip_single_page.json")),
    ]
    with _transport() as t:
        envelope = t.request_json("GET", "/v1/list/trip")
    assert len(envelope.trips) == 2
    assert route.call_count == 2


@respx.mock
def test_500_gives_up_with_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep_retry(monkeypatch)
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(500, text="oh no")
    )
    with _transport() as t, pytest.raises(TripItServerError):
        t.request_json("GET", "/v1/list/trip")


@respx.mock
def test_connect_error_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_sleep_retry(monkeypatch)
    route = respx.get("https://api.tripit.example/v1/list/trip")
    route.side_effect = [
        httpx.ConnectError("conn refused"),
        httpx.Response(200, json=_load("list_trip_single_page.json")),
    ]
    with _transport() as t:
        envelope = t.request_json("GET", "/v1/list/trip")
    assert len(envelope.trips) == 2


@respx.mock
def test_envelope_with_error_raises_api_error() -> None:
    respx.get("https://api.tripit.example/v1/get/trip").mock(
        return_value=httpx.Response(200, json=_load("error_response.json"))
    )
    with _transport() as t, pytest.raises(TripItAPIError) as exc_info:
        t.request_json("GET", "/v1/get/trip")
    assert exc_info.value.api_code == 404
    assert exc_info.value.entity_type == "Trip"


@respx.mock
def test_envelope_with_warning_is_logged_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, json=_load("warning_response.json"))
    )
    with _transport() as t, caplog.at_level(logging.WARNING, logger="tripit"):
        envelope = t.request_json("GET", "/v1/list/trip")
    assert envelope.warnings
    assert any("tripit warning" in r.message for r in caplog.records)


@respx.mock
def test_invalid_json_raises_validation_error() -> None:
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, text="<html>nope</html>")
    )
    with _transport() as t, pytest.raises(TripItValidationError):
        t.request_json("GET", "/v1/list/trip")


@respx.mock
def test_transport_error_wraps_unexpected_httpx_error() -> None:
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        side_effect=httpx.UnsupportedProtocol("wat")
    )
    with _transport() as t, pytest.raises(TripItTransportError):
        t.request_json("GET", "/v1/list/trip")


@respx.mock
def test_format_json_is_always_sent() -> None:
    route = respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, json=_load("list_trip_single_page.json"))
    )
    with _transport() as t:
        t.request_json("GET", "/v1/list/trip", params={"page_num": "1"})
    assert route.calls.last.request.url.params["format"] == "json"


@respx.mock
def test_request_raw_returns_wire_json_unparsed() -> None:
    """request_raw must return the dict as-sent, including keys the pydantic models
    would have dropped via extra="ignore"."""
    payload_with_unknown = {
        "Response": {
            "timestamp": 1700000000,
            "num_bytes": 256,
            "Trip": [{"id": "1", "display_name": "X", "tripit_secret_future_field": "y"}],
            "envelope_level_future_field": "z",
        }
    }
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(200, json=payload_with_unknown)
    )
    with _transport() as t:
        raw = t.request_raw("GET", "/v1/list/trip")
    assert raw == payload_with_unknown  # full fidelity


@respx.mock
def test_request_raw_still_raises_typed_errors_on_4xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_sleep_retry(monkeypatch)
    respx.get("https://api.tripit.example/v1/list/trip").mock(
        return_value=httpx.Response(429, headers={"retry-after": "1"}, text="slow")
    )
    with _transport() as t, pytest.raises(TripItRateLimitError):
        t.request_raw("GET", "/v1/list/trip")
