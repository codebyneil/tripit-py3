"""Live integration test that hits the real TripIt API.

Skipped by default. Run with:

    uv run pytest -m live tests/test_oauth_live.py -v

Required environment variables (or tripit_creds.json/tripit_tokens.json in
the project root):

    TRIPIT_CONSUMER_KEY
    TRIPIT_CONSUMER_SECRET
    TRIPIT_ACCESS_TOKEN
    TRIPIT_ACCESS_TOKEN_SECRET

If access tokens are missing, the test skips with instructions to run the
capture script first to mint them.

What this test exercises:

  1. OAuth 1.0 signing against the live `/v1/get/profile` endpoint.
  2. Strict pydantic-xml parsing of a real, non-curated Profile — if a live
     account's Profile carries an out-of-schema element, strict mode will
     surface it here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tripit import TripIt
from tripit.exceptions import TripItError

pytestmark = pytest.mark.live


def _load_secret(name: str) -> str | None:
    """Resolve a secret from env, falling back to tripit_creds.json /
    tripit_tokens.json at the project root.
    """
    value = os.environ.get(name)
    if value:
        return value

    project_root = Path(__file__).parent.parent
    file_keys = {
        "TRIPIT_CONSUMER_KEY": ("tripit_creds.json", ("consumer_key", "api_key")),
        "TRIPIT_CONSUMER_SECRET": (
            "tripit_creds.json",
            ("consumer_secret", "api_secret"),
        ),
        "TRIPIT_ACCESS_TOKEN": ("tripit_tokens.json", ("access_token",)),
        "TRIPIT_ACCESS_TOKEN_SECRET": ("tripit_tokens.json", ("access_token_secret",)),
    }
    if name not in file_keys:
        return None
    filename, keys = file_keys[name]
    path = project_root / filename
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    for key in keys:
        if data.get(key):
            return data[key]
    return None


@pytest.fixture(scope="module")
def live_client() -> TripIt:
    consumer_key = _load_secret("TRIPIT_CONSUMER_KEY")
    consumer_secret = _load_secret("TRIPIT_CONSUMER_SECRET")
    access_token = _load_secret("TRIPIT_ACCESS_TOKEN")
    access_token_secret = _load_secret("TRIPIT_ACCESS_TOKEN_SECRET")

    missing = [
        n
        for n, v in [
            ("consumer_key", consumer_key),
            ("consumer_secret", consumer_secret),
            ("access_token", access_token),
            ("access_token_secret", access_token_secret),
        ]
        if not v
    ]
    if missing:
        pytest.skip(
            "Missing live credentials: " + ", ".join(missing) + ". "
            "Run `uv run python scripts/capture_fixtures.py` to mint tokens."
        )

    # `cast`-ish — we just verified non-None above.
    client = TripIt(
        consumer_key=consumer_key,  # type: ignore[arg-type]
        consumer_secret=consumer_secret,  # type: ignore[arg-type]
        token=access_token,  # type: ignore[arg-type]
        token_secret=access_token_secret,  # type: ignore[arg-type]
    )
    yield client
    client.close()


def test_get_profile_returns_real_profile(live_client: TripIt) -> None:
    """OAuth signing + Profile parsing against the real API."""
    profile = live_client.get_profile()
    assert profile.screen_name, "Profile should have a screen_name on a real account"


def test_list_trips_yields_typed_trips(live_client: TripIt) -> None:
    """Paginated read against the real API; round-trip envelope through models."""
    try:
        trips = list(live_client.list_trips(past=True, page_size=25))
    except TripItError:
        pytest.fail("list_trips(past=True) raised — see traceback")
    # Account may have zero trips; we only check the list is well-typed.
    for t in trips:
        assert t.id, "Each Trip must have an id"
