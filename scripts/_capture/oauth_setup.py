"""Two-phase 3-legged OAuth dance with separate token cache.

The capture script may run non-interactively (no TTY-backed stdin), so we
can't block on `readline()` waiting for the user to press Enter after a
browser approval. Instead we split the dance across runs:

  - **Phase 1** (no pending RT cached): fetch a fresh request token, save
    it to `tripit_tokens.json`, raise `OAuthApprovalRequired` with the
    authorize URL. The caller exits 0 with friendly instructions.
  - **Phase 2** (pending RT cached): try to exchange the stored request
    token for an access token. Success → cache AT, clear pending RT,
    continue. Failure → re-raise `OAuthApprovalRequired` with the *same*
    URL (the user just hasn't approved yet, or approved a stale token);
    do **not** mint a new request token unless `--refresh-oauth` is set.

If `programmatic_login.approve_request_token()` succeeds inside phase 1,
phase 2 collapses into the same run with no user action needed.
"""

from __future__ import annotations

import logging

from scripts._capture.credentials import Credentials
from scripts._capture.programmatic_login import approve_request_token
from scripts._capture.tokens import (
    Tokens,
    save_access_token,
    save_pending_request_token,
)
from tripit.auth import (
    AccessToken,
    authorization_url,
    get_access_token,
    get_request_token,
)
from tripit.exceptions import TripItError

logger = logging.getLogger("tripit.capture")


class OAuthApprovalRequired(RuntimeError):
    """Raised when a request token needs user browser approval (or re-approval)."""

    def __init__(self, auth_url: str, *, reason: str = "approval required") -> None:
        super().__init__(f"{reason}: open {auth_url}")
        self.auth_url = auth_url
        self.reason = reason


def ensure_access_token(
    creds: Credentials,
    tokens: Tokens,
    *,
    force: bool = False,
    api_url: str = "https://api.tripit.com",
    web_url: str = "https://www.tripit.com",
) -> tuple[Tokens, AccessToken]:
    """Return a usable (tokens, access_token) pair, doing the OAuth dance if needed.

    Raises `OAuthApprovalRequired` when the caller must visit a URL in their
    browser. Returns normally only when an access token is in hand.
    """
    if not force and tokens.has_access_token():
        logger.info("Using cached access token from tripit_tokens.json")
        assert tokens.access_token
        assert tokens.access_token_secret
        return tokens, AccessToken(
            oauth_token=tokens.access_token,
            oauth_token_secret=tokens.access_token_secret,
        )

    # Phase 2: a request token from a previous run is sitting in the tokens
    # file. The user has presumably approved it in their browser by now —
    # try to exchange it.
    if not force and tokens.has_pending_request_token():
        assert tokens.pending_request_token
        assert tokens.pending_request_token_secret
        logger.info("Pending request token found — attempting exchange...")
        try:
            access_token = get_access_token(
                creds.consumer_key,
                creds.consumer_secret,
                tokens.pending_request_token,
                tokens.pending_request_token_secret,
                api_url=api_url,
            )
        except TripItError as exc:
            # Don't mint a new request token. The most common case is that
            # the user hasn't approved this one yet; re-print the SAME URL
            # so subsequent retries land on the same approval link.
            logger.warning("Exchange failed: %s", exc)
            same_url = authorization_url(tokens.pending_request_token, web_url=web_url)
            raise OAuthApprovalRequired(
                same_url,
                reason=(
                    "request token not yet approved (or now invalid). "
                    "Approve in browser, then re-run. If the URL gives "
                    '"Access Request Failed", run with --refresh-oauth.'
                ),
            ) from exc
        else:
            tokens = save_access_token(
                tokens,
                access_token=access_token.oauth_token,
                access_token_secret=access_token.oauth_token_secret,
            )
            logger.info("Access token cached to tripit_tokens.json")
            return tokens, access_token

    # Phase 1: get a fresh request token.
    logger.info("Fetching request token...")
    request_token = get_request_token(creds.consumer_key, creds.consumer_secret, api_url=api_url)

    logger.info("Attempting programmatic OAuth approval...")
    if approve_request_token(creds, request_token.oauth_token, web_url=web_url):
        logger.info("Programmatic approval succeeded — exchanging now")
        access_token = get_access_token(
            creds.consumer_key,
            creds.consumer_secret,
            request_token.oauth_token,
            request_token.oauth_token_secret,
            api_url=api_url,
        )
        tokens = save_access_token(
            tokens,
            access_token=access_token.oauth_token,
            access_token_secret=access_token.oauth_token_secret,
        )
        return tokens, access_token

    # Programmatic approval failed (e.g. Akamai blocked it). Save the request
    # token to the tokens file and hand control back.
    tokens = save_pending_request_token(
        tokens,
        request_token=request_token.oauth_token,
        request_token_secret=request_token.oauth_token_secret,
    )
    auth_url = authorization_url(request_token.oauth_token, web_url=web_url)
    raise OAuthApprovalRequired(auth_url, reason="fresh approval required")
