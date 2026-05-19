"""OAuth dance variants: localhost listener (primary), then two-phase fallback.

There are three ways to complete the user-approval step:

  1. **Localhost listener** (preferred). Caller registers
     `http://localhost:<port>/callback` as a redirect URI on the TripIt
     developer console, then runs the capture script with that URL as the
     `oauth_callback`. The script opens the authorize URL in the user's
     browser and blocks on a tiny local HTTP server until TripIt redirects
     the browser back with `oauth_token` + `oauth_verifier`. Synchronous
     end-to-end — no manual copy/paste, no re-runs.
  2. **Programmatic login** (best-effort). `programmatic_login.py` tries
     to do the browser approval via httpx scraping. Usually blocked by
     Akamai Bot Manager today, but if it ever works the script captures
     in one go.
  3. **Two-phase manual** (last resort). Mint RT, exit, user approves in
     browser at their own pace, re-run to exchange. Used when no listener
     port is given and programmatic login fails.

If `programmatic_login.approve_request_token()` succeeds, phase 2 collapses
into the same run with no user action needed.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import sys

from scripts._capture.credentials import Credentials
from scripts._capture.local_listener import (
    DEFAULT_PORT,
    CallbackTimeout,
    wait_for_callback,
)
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


def _open_in_browser(url: str) -> None:
    """Best-effort: open `url` in the system default browser."""
    if sys.platform == "darwin":
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(["open", url], check=False, timeout=5)


def ensure_access_token(
    creds: Credentials,
    tokens: Tokens,
    *,
    force: bool = False,
    api_url: str = "https://api.tripit.com",
    web_url: str = "https://www.tripit.com",
    listen_port: int | None = DEFAULT_PORT,
    callback_url: str | None = None,
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

    # Phase 1: get a fresh request token. If we have a callback, register it
    # with TripIt so the issued token is bound to it.
    effective_callback = callback_url
    if effective_callback is None and listen_port is not None:
        # HTTPS — TripIt's developer console rejects plain http callbacks.
        effective_callback = f"https://127.0.0.1:{listen_port}/callback"

    logger.info("Fetching request token (oauth_callback=%s)...", effective_callback)
    request_token = get_request_token(
        creds.consumer_key,
        creds.consumer_secret,
        oauth_callback=effective_callback,
        api_url=api_url,
    )

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

    # Localhost listener flow — open the URL, block on the callback.
    if listen_port is not None and effective_callback and "127.0.0.1" in effective_callback:
        # Include oauth_callback on the authorize URL too — tripper's working
        # Next.js implementation does this and TripIt seemingly requires it,
        # even though their docs say it's optional once registered.
        auth_url = authorization_url(
            request_token.oauth_token,
            callback_url=effective_callback,
            web_url=web_url,
        )
        logger.info(
            "Opening authorize URL in browser; listening on port %d...",
            listen_port,
        )
        sys.stderr.write(
            f"\nIf your browser doesn't open automatically, paste this URL:\n  {auth_url}\n\n"
        )
        _open_in_browser(auth_url)
        try:
            params = wait_for_callback(port=listen_port, timeout=300.0)
        except CallbackTimeout as exc:
            tokens = save_pending_request_token(
                tokens,
                request_token=request_token.oauth_token,
                request_token_secret=request_token.oauth_token_secret,
            )
            raise OAuthApprovalRequired(
                auth_url, reason=f"local listener timed out: {exc}"
            ) from exc

        if params.get("oauth_token") != request_token.oauth_token:
            logger.warning(
                "Callback oauth_token %r != request token %r; exchanging anyway",
                params.get("oauth_token"),
                request_token.oauth_token,
            )
        oauth_verifier = params.get("oauth_verifier")

        logger.info("Exchanging request token for access token...")
        access_token = get_access_token(
            creds.consumer_key,
            creds.consumer_secret,
            request_token.oauth_token,
            request_token.oauth_token_secret,
            oauth_verifier=oauth_verifier,
            api_url=api_url,
        )
        tokens = save_access_token(
            tokens,
            access_token=access_token.oauth_token,
            access_token_secret=access_token.oauth_token_secret,
        )
        return tokens, access_token

    # No listener — fall back to two-phase manual.
    tokens = save_pending_request_token(
        tokens,
        request_token=request_token.oauth_token,
        request_token_secret=request_token.oauth_token_secret,
    )
    auth_url = authorization_url(
        request_token.oauth_token,
        callback_url=effective_callback,
        web_url=web_url,
    )
    raise OAuthApprovalRequired(auth_url, reason="fresh approval required")
