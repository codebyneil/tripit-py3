"""Tiny localhost HTTPS listener to catch the OAuth callback after user approval.

TripIt's developer console only accepts `https://` redirect URIs, so the
listener has to terminate TLS even though we're binding to 127.0.0.1. We
generate a self-signed cert + key on the fly via `openssl` (one-shot, into
the OS temp dir; deleted after the listener exits). The browser will warn
about the untrusted cert the first time — the user clicks through once.

Flow:
  1. We send `oauth_callback=https://127.0.0.1:<port>/callback` when fetching
     the request token.
  2. We open the authorize URL in the user's browser; they approve.
  3. TripIt redirects them to our listener with
     `oauth_token=<RT>&oauth_verifier=<V>` in the query string.
  4. `wait_for_callback()` returns those params; the caller exchanges them
     for an access token.

The listener serves a single request and shuts itself down. Binds to
127.0.0.1 only (never the public interface); silences default request
logging so captured params don't end up on stderr.
"""

from __future__ import annotations

import contextlib
import http.server
import logging
import socketserver
import ssl
import subprocess
import tempfile
import threading
from pathlib import Path
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


def _generate_self_signed_cert(host: str) -> tuple[Path, Path]:
    """Generate a 1-day self-signed cert + key in the OS temp dir.

    Uses `openssl` (present on macOS / most dev boxes). Caller is responsible
    for cleaning up via `_cleanup_cert`.
    """
    tmp = Path(tempfile.mkdtemp(prefix="tripit-capture-tls-"))
    key_path = tmp / "key.pem"
    cert_path = tmp / "cert.pem"
    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-days",
                "1",
                "-nodes",
                "-subj",
                f"/CN={host}",
            ],
            check=True,
            capture_output=True,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError(
            "Couldn't generate self-signed TLS cert via `openssl`. "
            f"Is openssl on PATH? Underlying error: {exc}"
        ) from exc
    return cert_path, key_path


def _cleanup_cert(cert_path: Path, key_path: Path) -> None:
    for p in (cert_path, key_path):
        with contextlib.suppress(OSError):
            p.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        cert_path.parent.rmdir()


def wait_for_callback(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 300.0,
) -> dict[str, str]:
    """Block until TripIt redirects to https://<host>:<port>/...

    Returns the query-string params from that redirect. Raises
    `CallbackTimeout` if no callback arrives within `timeout` seconds.
    """
    cert_path, key_path = _generate_self_signed_cert(host)
    try:
        server = _CallbackServer((host, port), _CallbackHandler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)

        logger.info("Listening on https://%s:%d/ for OAuth redirect...", host, port)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        try:
            if server.captured_params is None:
                server.shutdown()
                raise CallbackTimeout(
                    f"No OAuth callback received within {timeout:.0f}s. "
                    f"Did you approve in the browser?"
                )
            return server.captured_params
        finally:
            server.server_close()
    finally:
        _cleanup_cert(cert_path, key_path)
