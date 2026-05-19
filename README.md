# tripit

Modern Python 3 client for the TripIt v1 API. Synchronous, typed, robust.

> v1.0.0 is a complete rewrite. The 0.x API (`OAuthConsumerCredential`,
> `TravelObj`, XML SAX parsing, `_parse_command` magic) is gone.

## Install

```bash
uv add tripit
```

## Quickstart

```python
from tripit import TripIt

with TripIt(
    consumer_key="...", consumer_secret="...",
    token="...",        token_secret="...",
) as client:
    profile = client.get_profile()           # (Phase 2)
    for trip in client.list_trips(past=False):
        print(trip.id, trip.start_date, trip.display_name)
```

## OAuth flow

3-legged OAuth 1.0a. Use the bundled CLI:

```bash
uv run tripit-authorize --consumer-key K --consumer-secret S
```

It walks you through the request-token → authorization → access-token dance
and prints tokens you can plug into the `TripIt(...)` constructor above.

Or do it programmatically:

```python
from tripit.auth import get_request_token, authorization_url, get_access_token

rt = get_request_token(consumer_key, consumer_secret)
print("Visit:", authorization_url(rt.oauth_token, callback_url="oob"))
input("Press Enter after approving...")
at = get_access_token(
    consumer_key, consumer_secret,
    rt.oauth_token, rt.oauth_token_secret,
)
print("token =", at.oauth_token)
print("token_secret =", at.oauth_token_secret)
```

## What works (Phase 1)

- OAuth 1.0a signing (HMAC-SHA1), including signature inclusion of form bodies
  on POST writes
- `get_trip(id)` and `list_trips()` with auto-pagination
- Typed `Trip`, `Address`, `Response`, `Error`, `Warning` models
- Retries on 429 / 5xx / transient network errors with exponential backoff
- Typed exception hierarchy under `TripItError`

Phase 2 adds the remaining read endpoints + full model coverage; Phase 3 adds
writes (`create_*`, `replace_*`, `delete_*`, CRS) backed by lxml XML
serialization.

## Development

```bash
uv sync                     # install
uv run pytest               # unit tests + coverage
uv run ruff check .         # lint
uv run ruff format .        # format
uv run ty check src/        # type check
uv run pre-commit install   # hook installer
```

## License

Apache 2.0 — see `LICENSE.md`. Original TripIt API bindings (c) 2008–2018
Concur Technologies, Inc. This rewrite preserves the original copyright and
license terms.
