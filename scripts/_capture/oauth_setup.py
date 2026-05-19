"""One-time 3-legged OAuth dance with persistent caching.

`ensure_access_token(creds)` returns the cached access token if present,
otherwise runs the full handshake (request_token → user-approval →
access_token), caches the result in `tripit_creds.json`, and returns it.

The user-approval step is handled by `manual_approval()` — print the URL,
wait for the user to click Approve in a browser, then exchange. A
programmatic httpx-based variant slots in front of this in step 4
(`programmatic_login.py`).
"""

from __future__ import annotations

import logging

from scripts._capture.credentials import Credentials, save_access_token
from scripts._capture.programmatic_login import approve_request_token
from tripit.auth import (
    AccessToken,
    authorization_url,
    get_access_token,
    get_request_token,
)
from tripit.cli.authorize import wait_for_manual_approval

logger = logging.getLogger("tripit.capture")


def ensure_access_token(
    creds: Credentials,
    *,
    force: bool = False,
    api_url: str = "https://api.tripit.com",
    web_url: str = "https://www.tripit.com",
) -> tuple[Credentials, AccessToken]:
    """Return a usable (creds, access_token) pair, doing the OAuth dance if needed.

    - If `creds.access_token` is set and `force` is False, reuse it.
    - Otherwise: get request token, walk the user through approval (manual for
      now; programmatic added in step 4), exchange for access token, persist
      back to the creds file.
    """
    if not force and creds.access_token and creds.access_token_secret:
        logger.info("Using cached access token from tripit_creds.json")
        return creds, AccessToken(
            oauth_token=creds.access_token,
            oauth_token_secret=creds.access_token_secret,
        )

    logger.info("Fetching request token...")
    request_token = get_request_token(creds.consumer_key, creds.consumer_secret, api_url=api_url)

    logger.info("Attempting programmatic OAuth approval...")
    if approve_request_token(creds, request_token.oauth_token, web_url=web_url):
        logger.info("Programmatic approval succeeded")
    else:
        logger.info("Programmatic approval failed — falling back to manual")
        auth_url = authorization_url(request_token.oauth_token, web_url=web_url)
        wait_for_manual_approval(auth_url)

    logger.info("Exchanging for access token...")
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
    logger.info("Access token cached to tripit_creds.json")
    return updated_creds, access_token
