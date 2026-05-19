"""Script-managed OAuth token cache, kept separate from user credentials.

`tripit_creds.json` is the user-managed file containing the four secrets the
user provides (consumer key + secret + username + password). The capture
script *never* writes to it.

This module owns `tripit_tokens.json` — a separate file the script writes
to, holding the cached OAuth access token and any pending-but-not-yet-
exchanged request token. If the file doesn't exist on disk, `load_tokens()`
returns an empty `Tokens()` instance.
"""

from __future__ import annotations

import json
import stat
from dataclasses import asdict, dataclass, replace
from pathlib import Path

TOKENS_PATH = Path("tripit_tokens.json")


@dataclass(frozen=True)
class Tokens:
    access_token: str | None = None
    access_token_secret: str | None = None
    pending_request_token: str | None = None
    pending_request_token_secret: str | None = None

    def has_access_token(self) -> bool:
        return bool(self.access_token and self.access_token_secret)

    def has_pending_request_token(self) -> bool:
        return bool(self.pending_request_token and self.pending_request_token_secret)


def load_tokens(path: Path = TOKENS_PATH) -> Tokens:
    """Read cached tokens. Returns empty `Tokens()` if the file isn't present."""
    if not path.exists():
        return Tokens()
    data = json.loads(path.read_text())
    return Tokens(
        access_token=data.get("access_token") or None,
        access_token_secret=data.get("access_token_secret") or None,
        pending_request_token=data.get("pending_request_token") or None,
        pending_request_token_secret=data.get("pending_request_token_secret") or None,
    )


def save_access_token(
    tokens: Tokens,
    *,
    access_token: str,
    access_token_secret: str,
    path: Path = TOKENS_PATH,
) -> Tokens:
    """Persist a new access token (clearing any stale pending request token)."""
    updated = replace(
        tokens,
        access_token=access_token,
        access_token_secret=access_token_secret,
        pending_request_token=None,
        pending_request_token_secret=None,
    )
    _write(path, updated)
    return updated


def save_pending_request_token(
    tokens: Tokens,
    *,
    request_token: str,
    request_token_secret: str,
    path: Path = TOKENS_PATH,
) -> Tokens:
    """Stash a request token between phases 1 and 2 of the OAuth dance."""
    updated = replace(
        tokens,
        pending_request_token=request_token,
        pending_request_token_secret=request_token_secret,
    )
    _write(path, updated)
    return updated


def clear_tokens(path: Path = TOKENS_PATH) -> Tokens:
    """Erase the on-disk cache (used by --refresh-oauth)."""
    if path.exists():
        path.unlink()
    return Tokens()


def _write(path: Path, tokens: Tokens) -> None:
    path.write_text(json.dumps(asdict(tokens), indent=2) + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
