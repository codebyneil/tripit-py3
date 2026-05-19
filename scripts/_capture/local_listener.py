"""Tiny localhost HTTP listener to catch the OAuth callback after user approval.

Flow:
  1. We send `oauth_callback=http://localhost:<port>/callback` when fetching
     the request token.
  2. We open the authorize URL in the user's browser; they approve.
  3. TripIt redirects them to our localhost listener with
     `oauth_token=<RT>&oauth_verifier=<V>` in the query string.
  4. `wait_for_callback()` returns those params; the caller exchanges them
     for an access token.

The listener serves a single request and shuts itself down. It binds to
127.0.0.1 only (never the public interface) and silences default request
logging so the captured params don't end up on stderr.
"""

from __future__ import annotations

import http.server
import logging
import socketserver
import threading
from typing import Any
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger("tripit.capture.listener")

DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


_SUCCESS_HTML = (
    b"<!DOCTYPE html>\n"
    b"<html><head><title>TripIt OAuth - Authorized</title>\n"
    b"<style>body{font-family:system-ui,sans-serif;max-width:560px;"
    b"margin:80px auto;padding:0 16px;line-height:1.5}"
    b"h1{color:#0a7d3a}</style>\n"
    b"</head><body>\n"
    b"<h1>Authorized.</h1>\n"
    b"<p>You can close this tab. The capture script has the verifier and "
    b"will exchange it for an access token.</p>\n"
    b"</body></html>\n"
)


class _CallbackServer(socketserver.TCPServer):
    """Single-shot HTTP server. `captured_params` gets set by the handler."""

    allow_reuse_address = True
    captured_params: dict[str, str] | None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.captured_params = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    server: _CallbackServer  # type: ignore[assignment]

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        # parse_qs gives list values; flatten to single values for our use.
        raw = parse_qs(parsed.query, keep_blank_values=True)
        flat = {k: v[0] for k, v in raw.items() if v}
        self.server.captured_params = flat

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(_SUCCESS_HTML)))
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML)

        # Schedule server shutdown from a fresh thread — shutdown() blocks until
        # serve_forever() returns, which can't happen from inside a handler.
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: Any) -> None:
        # Silence default stderr access-log so captured params don't leak.
        return


class CallbackTimeout(RuntimeError):
    """Listener timed out before TripIt redirected the user back."""


def wait_for_callback(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 300.0,
) -> dict[str, str]:
    """Block until TripIt redirects to http://<host>:<port>/...

    Returns the query-string params from that redirect. Raises
    `CallbackTimeout` if no callback arrives within `timeout` seconds.
    """
    server = _CallbackServer((host, port), _CallbackHandler)
    logger.info("Listening on http://%s:%d/ for OAuth redirect...", host, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    try:
        if server.captured_params is None:
            server.shutdown()
            raise CallbackTimeout(
                f"No OAuth callback received within {timeout:.0f}s. Did you approve in the browser?"
            )
        return server.captured_params
    finally:
        server.server_close()
