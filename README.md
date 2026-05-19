# tripit

Modern Python 3 client for the TripIt v1 API. Synchronous, typed, robust.

[![CI](https://github.com/codebyneil/tripit-py3/actions/workflows/ci.yml/badge.svg)](https://github.com/codebyneil/tripit-py3/actions)

> v1.0.0 is a complete rewrite. The 0.x API (`OAuthConsumerCredential`,
> `TravelObj`, XML SAX parsing, `_parse_command` magic) is gone. See
> [`docs/migration-from-0.x.md`](docs/migration-from-0.x.md) for the mapping.

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

## Development

```bash
uv sync                     # install + dev deps
uv run pytest               # tests + coverage
uv run ruff check .         # lint
uv run ruff format .        # format
uv run ty check src/        # type check
uv run pre-commit install   # install hooks
```

## License

Apache 2.0 — see `LICENSE.md`. Original TripIt API bindings (c) 2008–2018
Concur Technologies, Inc. This rewrite preserves the original copyright and
license terms.
