"""User credentials loader — reads from `tripit_creds.json` (and env fallbacks).

The script never writes to this file. Token caching lives in `tokens.py`.

Resolution order for each required field (consumer key + secret + username +
password):
  1. Value present in `tripit_creds.json` (either canonical name like
     `consumer_key` or compact alias like `api_key`).
  2. Corresponding TRIPIT_* environment variable.
  3. Raise `MissingCredentialsError`.

Any extra keys in `tripit_creds.json` — including legacy `access_token` /
`pending_request_token` fields a buggy earlier version of this script may
have written — are silently ignored.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CREDS_PATH = Path("tripit_creds.json")

_REQUIRED_FIELDS = ("consumer_key", "consumer_secret", "username", "password")

_ENV_NAMES = {
    "consumer_key": "TRIPIT_CONSUMER_KEY",
    "consumer_secret": "TRIPIT_CONSUMER_SECRET",
    "username": "TRIPIT_USERNAME",
    "password": "TRIPIT_PASSWORD",
}

# Accept compact alternative field names in the JSON file.
_FILE_KEY_ALIASES = {
    "api_key": "consumer_key",
    "api_secret": "consumer_secret",
    "user": "username",
    "pass": "password",
    "consumer_key": "consumer_key",
    "consumer_secret": "consumer_secret",
    "username": "username",
    "password": "password",
}


@dataclass(frozen=True)
class Credentials:
    consumer_key: str
    consumer_secret: str
    username: str
    password: str


class MissingCredentialsError(RuntimeError):
    """One or more required credential fields could not be resolved."""


def load_credentials(path: Path = CREDS_PATH) -> Credentials:
    """Resolve credentials from `path` with env-var fallback."""
    file_data: dict[str, str] = {}
    if path.exists():
        raw = json.loads(path.read_text())
        for key, value in raw.items():
            canonical = _FILE_KEY_ALIASES.get(key)
            if canonical and isinstance(value, str):
                file_data[canonical] = value

    resolved: dict[str, str | None] = {}
    for field in _REQUIRED_FIELDS:
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
    )
