# tripit

Modern Python 3 client for the TripIt v1 API. Synchronous, typed, robust.

[![CI](https://github.com/codebyneil/tripit-py3/actions/workflows/ci.yml/badge.svg)](https://github.com/codebyneil/tripit-py3/actions)

> v2.0.0 — TripIt's `/oauth/authorize` now requires the registered callback
> URL to be passed on both the request-token call and the authorize URL.
> The client supports the full 1.0a callback + verifier round-trip plus a
> bundled localhost-listener helper. Several model fields were corrected
> against real API captures (notably `NotificationSetting` was rewritten).

## Highlights

- Sync HTTP via `httpx.Client` — one chokepoint, explicit timeouts, connection pooling
- OAuth 1.0a signing as an `httpx.Auth` (handles form-body inclusion in the signature)
- Typed pydantic v2 models for every TripIt v1 XSD type — 74 types in total
- JSON-only on reads, lxml-built XML on writes
- Auto-pagination on `list_*` endpoints
- Typed exception hierarchy under `TripItError` — `TripItRateLimitError`,
  `TripItAuthError`, `TripItServerError`, etc.
- Retries 429/5xx/transient network errors with exponential backoff + Retry-After honor
- Managed by [uv](https://docs.astral.sh/uv/), linted by [ruff](https://docs.astral.sh/ruff/),
  type-checked by [ty](https://docs.astral.sh/ty/)

## Install

```bash
uv add tripit
```

## Quickstart

Get tokens once with the bundled CLI:

```bash
uv run tripit-authorize --consumer-key K --consumer-secret S
```

Then use the client:

```python
from tripit import TripIt

with TripIt(
    consumer_key="...", consumer_secret="...",
    token="...",        token_secret="...",
) as client:
    me = client.get_profile()
    print(me.public_display_name, me.home_city)

    for trip in client.list_trips(past=False):
        print(trip.id, trip.start_date, trip.display_name)
```

## Reads

```python
client.get_trip("999000111222")
client.list_trips(past=True, traveler="only", page_size=100)
client.get_profile()
client.list_points_programs()
client.get_air("555111")          # AirObject with typed Segment[], FlightStatus
client.get_lodging("555222")      # LodgingObject
client.get_car("555333")
client.get_rail("555444")
client.get_transport("555555")
client.get_cruise("555666")
client.get_restaurant("555777")
client.get_activity("555888")
client.get_note("555999")
client.get_map("556111")
client.get_directions("556222")
client.get_parking("556333")

# Multi-type pagination — yields each page envelope so you see every kind:
for page in client.list_objects_envelope(trip_id="999000111222"):
    for air in page.air_objects: ...
    for lodging in page.lodging_objects: ...
```

## Writes

```python
from datetime import date
from tripit import Trip, AirObject, AirSegment, DateTime

trip = client.create_trip(Trip(
    start_date=date(2026, 6, 1),
    end_date=date(2026, 6, 3),
    display_name="Tokyo",
    primary_location="Tokyo, JP",
))

client.replace_trip(trip.id, Trip(display_name="Tokyo (renamed)"))
client.delete_trip(trip.id)
```

The same `create_<entity>` / `replace_<entity>` / `delete_<entity>` triplet
exists for every TripIt object type. The pydantic model gets serialized into
an XML `<Request>` envelope, OAuth-signed, and POSTed as
`application/x-www-form-urlencoded` — the way TripIt's write endpoints expect.

CRS partner-agency endpoints accept raw XML payloads since their shapes vary
widely:

```python
client.crs_load_reservations(xml_payload, company_key="...")
client.crs_delete_reservations("LOC-ABC-123")
```

## Errors

```python
from tripit import (
    TripItError, TripItAuthError, TripItRateLimitError,
    TripItServerError, TripItNotFoundError, TripItAPIError,
    TripItValidationError, TripItTransportError,
)

try:
    trip = client.get_trip("does-not-exist")
except TripItNotFoundError:
    ...
except TripItRateLimitError as e:
    sleep(e.retry_after)
except TripItError:
    ...
```

The transport layer retries `TripItRateLimitError`, `TripItServerError`, and
transient httpx network errors (5 attempts, exponential jitter, honoring
`Retry-After`). Anything else propagates immediately.

## OAuth flow (programmatic)

```python
from tripit.auth import (
    get_request_token, authorization_url, get_access_token,
)

rt = get_request_token(consumer_key, consumer_secret)
print("Visit:", authorization_url(rt.oauth_token, callback_url="oob"))
input("Press Enter after approving...")
at = get_access_token(
    consumer_key, consumer_secret,
    rt.oauth_token, rt.oauth_token_secret,
)
# at.oauth_token, at.oauth_token_secret are the values you'd save and reuse
```

## Developer utility scripts

Two scripts live in `scripts/` for hacking on the library against a real account:

```bash
# Dump every trip + nested object to one JSON file
uv run python scripts/export_trips.py --output ~/Desktop/trips-backup.json --pretty

# Capture per-endpoint scrubbed fixtures into tests/fixtures/json/real_*.json
# (used by the round-trip + unknown-fields tests)
uv run python scripts/capture_fixtures.py
```

Both read credentials from `tripit_creds.json` (gitignored — never committed),
and cache OAuth access tokens to a separate `tripit_tokens.json`. The first
run opens a TripIt approval URL in your browser; subsequent runs reuse the
cached token. Register `https://127.0.0.1:8765/callback` as a redirect URI
on TripIt's developer console for the listener flow to work.

## Development

```bash
uv sync                     # install + dev deps
uv run pytest               # tests + coverage (skips live tests by default)
uv run pytest -m live       # also hit the real TripIt API (requires creds)
uv run ruff check .         # lint
uv run ruff format .        # format
uv run ty check src/        # type check
uv run pre-commit install   # install hooks
```

## License

Apache 2.0 — see `LICENSE.md`. Original TripIt API bindings (c) 2008–2018
Concur Technologies, Inc. This rewrite preserves the original copyright and
license terms.
