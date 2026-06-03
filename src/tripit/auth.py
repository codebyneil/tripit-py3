"""OAuth 1.0 signing for TripIt's v1 API.

TripIt implements OAuth **Core 1.0** (not 1.0a): the `oauth_callback` is passed
on the `/oauth/authorize` redirect, and there is no `oauth_verifier` /
`oauth_callback_confirmed` in the handshake. See
<https://tripit.github.io/api/doc/v1/#authentication>.

This module provides:
- `OAuth1Auth`, an `httpx.Auth` subclass that signs every outgoing request.
- Three module-level helpers (`get_request_token`, `authorization_url`,
  `get_access_token`) for the 3-legged OAuth handshake.

TripIt's write endpoints accept `application/x-www-form-urlencoded` bodies whose
fields MUST participate in the OAuth signature base string. We honor that by
parsing the body when the content type matches and folding those fields into the
signing inputs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl, quote, urlencode

import httpx

OAUTH_VERSION: Final = "1.0"
OAUTH_SIGNATURE_METHOD: Final = "HMAC-SHA1"
DEFAULT_API_URL: Final = "https://api.tripit.com"
_REQUEST_TOKEN_PATH: Final = "/oauth/request_token"
_ACCESS_TOKEN_PATH: Final = "/oauth/access_token"
_AUTHORIZE_PATH: Final = "/oauth/authorize"


def _escape(value: object) -> str:
    """OAuth percent-encoding (RFC 3986 unreserved chars + `~`)."""
    return quote(str(value), safe="~")


@dataclass(frozen=True)
class RequestToken:
    """Unauthorized request token returned by /oauth/request_token."""

    oauth_token: str
    oauth_token_secret: str


@dataclass(frozen=True)
class AccessToken:
    """Authorized access token returned by /oauth/access_token."""

    oauth_token: str
    oauth_token_secret: str


class OAuth1Auth(httpx.Auth):
    """httpx.Auth that signs every request with OAuth 1.0 HMAC-SHA1.

    Supports all three TripIt OAuth credential modes:
    - 2-legged (consumer key + secret + requestor_id)
    - 3-legged unauthenticated (consumer key + secret only)
    - 3-legged authenticated (consumer key + secret + token + token_secret)
    """

    requires_request_body = True

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        *,
        token: str | None = None,
        token_secret: str | None = None,
        requestor_id: str | None = None,
        _nonce: str | None = None,
        _timestamp: int | None = None,
    ) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._token = token or ""
        self._token_secret = token_secret or ""
        self._requestor_id = requestor_id or ""
        # Test-only injection points for deterministic signatures.
        self._fixed_nonce = _nonce
        self._fixed_timestamp = _timestamp

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = self._build_header(request)
        yield request

    def _build_header(self, request: httpx.Request) -> str:
        url = request.url
        method = request.method.upper()
        base_url = f"{url.scheme}://{url.host}{url.path}"

        oauth_params: dict[str, str] = {
            "oauth_consumer_key": self._consumer_key,
            "oauth_nonce": self._nonce(),
            "oauth_signature_method": OAUTH_SIGNATURE_METHOD,
            "oauth_timestamp": str(self._timestamp()),
            "oauth_version": OAUTH_VERSION,
        }
        if self._token:
            oauth_params["oauth_token"] = self._token
        if self._requestor_id:
            oauth_params["xoauth_requestor_id"] = self._requestor_id

        # Collect parameters that must participate in the signature base string.
        all_params: list[tuple[str, str]] = list(oauth_params.items())
        all_params.extend(
            (k, v) for k, v in parse_qsl(url.query.decode("ascii"), keep_blank_values=True)
        )
        all_params.extend(_form_body_params(request))

        signature = self._sign(method, base_url, all_params)
        oauth_params["oauth_signature"] = signature

        realm = f"{url.scheme}://{url.host}"
        header_pairs = [f'{_escape(k)}="{_escape(v)}"' for k, v in oauth_params.items()]
        return f'OAuth realm="{realm}",' + ",".join(header_pairs)

    def _sign(self, method: str, base_url: str, params: Iterable[tuple[str, str]]) -> str:
        # Per RFC 5849 §3.4.1.3.2: sort by encoded key, then encoded value.
        encoded = sorted((_escape(k), _escape(v)) for k, v in params if k != "oauth_signature")
        param_string = "&".join(f"{k}={v}" for k, v in encoded)
        base_string = "&".join([method, _escape(base_url), _escape(param_string)])
        key = f"{_escape(self._consumer_secret)}&{_escape(self._token_secret)}"
        digest = hmac.new(key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
        return base64.b64encode(digest).decode("ascii")

    def _nonce(self) -> str:
        if self._fixed_nonce is not None:
            return self._fixed_nonce
        return secrets.token_hex(16)

    def _timestamp(self) -> int:
        if self._fixed_timestamp is not None:
            return self._fixed_timestamp
        return int(time.time())


def _form_body_params(request: httpx.Request) -> list[tuple[str, str]]:
    """If the request is form-encoded, return its fields for signature inclusion."""
    content_type = request.headers.get("content-type", "").lower().split(";", 1)[0].strip()
    if content_type != "application/x-www-form-urlencoded":
        return []
    body = request.content
    if not body:
        return []
    return list(parse_qsl(body.decode("utf-8"), keep_blank_values=True))


def _exchange_token(
    consumer_key: str,
    consumer_secret: str,
    path: str,
    *,
    token: str | None = None,
    token_secret: str | None = None,
    body: dict[str, str] | None = None,
    api_url: str = DEFAULT_API_URL,
) -> dict[str, str]:
    auth = OAuth1Auth(
        consumer_key,
        consumer_secret,
        token=token,
        token_secret=token_secret,
    )
    # Per https://tripit.github.io/api/doc/v1/#authentication the request-token
    # and access-token endpoints are POST. (Some servers happen to accept GET
    # too, but the issued tokens may be flagged differently downstream — the
    # browser-facing /oauth/authorize page rejects RTs minted that way.)
    with httpx.Client(timeout=30.0) as client:
        if body:
            response = client.post(f"{api_url}{path}", data=body, auth=auth)
        else:
            response = client.post(f"{api_url}{path}", auth=auth)
    if response.status_code != 200:
        from tripit.exceptions import TripItAuthError

        raise TripItAuthError(
            f"Token exchange failed: HTTP {response.status_code}",
            status_code=response.status_code,
            response_body=response.text,
        )
    return dict(parse_qsl(response.text))


def get_request_token(
    consumer_key: str,
    consumer_secret: str,
    *,
    api_url: str = DEFAULT_API_URL,
) -> RequestToken:
    """First leg of the OAuth 1.0 flow: obtain an unauthorized request token.

    TripIt is OAuth Core 1.0, so the callback is NOT sent here — it goes on the
    `/oauth/authorize` redirect (see `authorization_url`).
    """
    data = _exchange_token(
        consumer_key,
        consumer_secret,
        _REQUEST_TOKEN_PATH,
        api_url=api_url,
    )
    return RequestToken(
        oauth_token=data["oauth_token"],
        oauth_token_secret=data["oauth_token_secret"],
    )


def authorization_url(
    token: str,
    callback_url: str | None = None,
    *,
    web_url: str = "https://www.tripit.com",
) -> str:
    """Build the URL the user must visit to authorize a request token."""
    params: dict[str, str] = {"oauth_token": token}
    if callback_url:
        params["oauth_callback"] = callback_url
    return f"{web_url}{_AUTHORIZE_PATH}?{urlencode(params)}"


def get_access_token(
    consumer_key: str,
    consumer_secret: str,
    request_token: str,
    request_token_secret: str,
    *,
    api_url: str = DEFAULT_API_URL,
) -> AccessToken:
    """Final leg of the OAuth 1.0 flow: exchange a user-authorized request token.

    TripIt is OAuth Core 1.0 and issues no `oauth_verifier`, so none is sent.
    """
    data = _exchange_token(
        consumer_key,
        consumer_secret,
        _ACCESS_TOKEN_PATH,
        token=request_token,
        token_secret=request_token_secret,
        api_url=api_url,
    )
    return AccessToken(
        oauth_token=data["oauth_token"],
        oauth_token_secret=data["oauth_token_secret"],
    )
