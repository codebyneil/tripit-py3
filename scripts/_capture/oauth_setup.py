"""Two-phase 3-legged OAuth dance with persistent caching.

The capture script runs non-interactively in many contexts (e.g. piped
output, no TTY), so we can't block on `stdin.readline()` waiting for the
user to press Enter after a browser approval. Instead we split the dance:

  - **Phase 1** (`ensure_access_token`, no pending RT yet): fetch a fresh
    request token, save it to `tripit_creds.json`, print the authorize URL
    via `OAuthApprovalRequired`, and let the caller exit cleanly.
  - **Phase 2** (`ensure_access_token`, pending RT cached): exchange the
    stored request token for an access token, persist that, clear the
    pending RT.

If `programmatic_login.approve_request_token()` succeeds inside phase 1,
phase 2 is folded into the same run — no user action required.
"""

from __future__ import annotations

import logging

from scripts._capture.credentials import (
    Credentials,
    save_access_token,
    save_pending_request_token,
)
from scripts._capture.programmatic_login import approve_request_token
from tripit.auth import (
    AccessToken,
    authorization_url,
    get_access_token,
    get_request_token,
)
from tripit.exceptions import TripItError

logger = logging.getLogger("tripit.capture")


class OAuthApprovalRequired(RuntimeError):
    """Raised mid-flow when a phase-1 request token needs user browser approval."""

    def __init__(self, auth_url: str) -> None:
        super().__init__(
            f"Open this URL in a browser, approve access, then re-run the "
            f"capture script: {auth_url}"
        )
        self.auth_url = auth_url


def ensure_access_token(
    creds: Credentials,
    *,
    force: bool = False,
    api_url: str = "https://api.tripit.com",
    web_url: str = "https://www.tripit.com",
) -> tuple[Credentials, AccessToken]:
    """Return a usable (creds, access_token) pair, doing the OAuth dance if needed.

    Raises `OAuthApprovalRequired` when the caller must visit a URL in their
    browser and re-run the script. Returns normally only when an access token
    is in hand (either cached, programmatically obtained, or exchanged from a
    previously-approved request token).
    """
    if not force and creds.access_token and creds.access_token_secret:
        logger.info("Using cached access token from tripit_creds.json")
        return creds, AccessToken(
            oauth_token=creds.access_token,
            oauth_token_secret=creds.access_token_secret,
        )

    # Phase 2: a request token from a previous run is sitting in the creds file.
    # The user has presumably approved it in their browser by now; try to
    # exchange it.
    if not force and creds.pending_request_token and creds.pending_request_token_secret:
        logger.info("Pending request token found — exchanging for access token...")
        try:
            access_token = get_access_token(
                creds.consumer_key,
                creds.consumer_secret,
                creds.pending_request_token,
                creds.pending_request_token_secret,
                api_url=api_url,
            )
        except TripItError as exc:
            logger.warning(
                "Stored request token didn't exchange (was it approved?): %s — "
                "starting a new approval round",
                exc,
            )
            # Fall through to phase 1.
        else:
            updated_creds = save_access_token(
                creds,
                access_token=access_token.oauth_token,
                access_token_secret=access_token.oauth_token_secret,
            )
            logger.info("Access token cached to tripit_creds.json")
            return updated_creds, access_token

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
        updated_creds = save_access_token(
            creds,
            access_token=access_token.oauth_token,
            access_token_secret=access_token.oauth_token_secret,
        )
        return updated_creds, access_token

    # Programmatic approval failed (e.g. Akamai blocked it). Save the request
    # token, print the URL, hand control back so the caller can exit cleanly
    # and the user can re-run after approving in their browser.
    save_pending_request_token(
        creds,
        request_token=request_token.oauth_token,
        request_token_secret=request_token.oauth_token_secret,
    )
    auth_url = authorization_url(request_token.oauth_token, web_url=web_url)
    raise OAuthApprovalRequired(auth_url)
