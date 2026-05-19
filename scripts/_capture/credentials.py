"""Credentials loading and access-token persistence for fixture capture.

The capture script needs four secrets up front (consumer key, consumer secret,
TripIt username, TripIt password) plus two cached values it writes itself
after the OAuth dance (access token + access token secret).

Resolution order for each input field:
  1. Value present in `.tripit-creds.json` (preferred — set chmod 0600)
  2. Corresponding TRIPIT_* environment variable
  3. Raise — missing required field.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass, replace
from pathlib import Path

CREDS_PATH = Path("tripit_creds.json")

_REQUIRED_FIELDS = ("consumer_key", "consumer_secret", "username", "password")

_ENV_NAMES = {
    "consumer_key": "TRIPIT_CONSUMER_KEY",
    "consumer_secret": "TRIPIT_CONSUMER_SECRET",
    "username": "TRIPIT_USERNAME",
    "password": "TRIPIT_PASSWORD",
    "access_token": "TRIPIT_ACCESS_TOKEN",
    "access_token_secret": "TRIPIT_ACCESS_TOKEN_SECRET",
}

# Map compact / alternative file keys onto our canonical field names so the
# user can write whichever form feels natural in `tripit_creds.json`.
_FILE_KEY_ALIASES = {
    "api_key": "consumer_key",
    "api_secret": "consumer_secret",
    "user": "username",
    "pass": "password",
    # Canonical names also pass through unchanged.
    "consumer_key": "consumer_key",
    "consumer_secret": "consumer_secret",
    "username": "username",
    "password": "password",
    "access_token": "access_token",
    "access_token_secret": "access_token_secret",
}


@dataclass(frozen=True)
class Credentials:
    consumer_key: str
    consumer_secret: str
    username: str
    password: str
    access_token: str | None = None
    access_token_secret: str | None = None


class MissingCredentialsError(RuntimeError):
    """One or more required credential fields could not be resolved."""


def load_credentials(path: Path = CREDS_PATH) -> Credentials:
    """Resolve credentials from `path` (JSON) with env-var fallbacks.

    The JSON file may use either canonical names (`consumer_key`, `username`,
    `password`, `consumer_secret`) or compact aliases (`api_key`, `api_secret`,
    `user`, `pass`). Raises `MissingCredentialsError` listing every
    required-but-missing field so the user sees the whole problem at once.
    """
    file_data: dict[str, str] = {}
    if path.exists():
        raw = json.loads(path.read_text())
        # Normalize aliases → canonical names.
        for key, value in raw.items():
            canonical = _FILE_KEY_ALIASES.get(key)
            if canonical:
                file_data[canonical] = value

    resolved: dict[str, str | None] = {}
    for field in (*_REQUIRED_FIELDS, "access_token", "access_token_secret"):
        value = file_data.get(field) or os.environ.get(_ENV_NAMES[field])
        resolved[field] = value or None

    missing = [f for f in _REQUIRED_FIELDS if not resolved[f]]
    if missing:
        raise MissingCredentialsError(
            "Missing credentials: "
            + ", ".join(missing)
            + f" — provide them in {path} or via env vars "
            + ", ".join(_ENV_NAMES[f] for f in missing)
        )

    # `or ""` keeps the type checker happy; we validated non-emptiness above.
    return Credentials(
        consumer_key=resolved["consumer_key"] or "",
        consumer_secret=resolved["consumer_secret"] or "",
        username=resolved["username"] or "",
        password=resolved["password"] or "",
        access_token=resolved["access_token"],
        access_token_secret=resolved["access_token_secret"],
    )


def save_access_token(
    creds: Credentials,
    *,
    access_token: str,
    access_token_secret: str,
    path: Path = CREDS_PATH,
) -> Credentials:
    """Persist the cached access token back to `.tripit-creds.json` (chmod 0600).

    Returns a new `Credentials` instance with the token fields filled in.
    """
    updated = replace(creds, access_token=access_token, access_token_secret=access_token_secret)
    path.write_text(json.dumps(asdict(updated), indent=2) + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    return updated
