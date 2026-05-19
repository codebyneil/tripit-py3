# Migrating from tripit 0.x to 1.0.0

Version 1.0.0 is a complete rewrite. The old API (0.2.0 and earlier) is gone.
This document maps the most common 0.x calls to their 1.0 equivalents.

## Construction

```python
# 0.x
import tripit
cred = tripit.OAuthConsumerCredential("ck", "cs", "token", "secret")
t = tripit.TripIt(cred)

# 1.0
from tripit import TripIt
with TripIt(consumer_key="ck", consumer_secret="cs",
            token="t", token_secret="ts") as t:
    ...
```

`TripIt` is a context manager — use `with` so the underlying HTTP connection
closes cleanly.

## Token-exchange helpers

```python
# 0.x
t = tripit.TripIt(tripit.OAuthConsumerCredential("ck", "cs"))
rt = t.get_request_token()
# ...user authorizes...
at = t.get_access_token()  # after replacing the credential with rt

# 1.0
from tripit.auth import get_request_token, authorization_url, get_access_token
rt = get_request_token("ck", "cs")
print(authorization_url(rt.oauth_token))
input("press enter")
at = get_access_token("ck", "cs", rt.oauth_token, rt.oauth_token_secret)
```

Or use `tripit-authorize` from your shell.

## Reads

| 0.x | 1.0 | Returns |
|---|---|---|
| `t.list_trip()` then `t.response` (XML) | `client.list_trips()` | `Iterator[Trip]` |
| `t.get_trip(id)` | `client.get_trip(id)` | `Trip` |
| `t.get_profile()` | `client.get_profile()` | `Profile` |
| `t.get_air(id)` | `client.get_air(id)` | `AirObject` |
| `t.get_lodging(id)` | `client.get_lodging(id)` | `LodgingObject` |
| (etc.) | (etc.) | (typed) |
| `t.list_points_program()` | `client.list_points_programs()` | `list[PointsProgram]` |
| `t.list_object()` | `client.list_objects_envelope()` | `Iterator[Response]` |

Reads return typed pydantic models with snake_case attribute names. PascalCase
nested types from the XSD are aliased; you can use either:

```python
trip.primary_location_address.city
trip.PrimaryLocationAddress.city  # ❌ AttributeError — use snake_case
```

## Writes

```python
# 0.x — caller built XML by hand
xml = "<Request><Trip>...</Trip></Request>"
t.create(xml)

# 1.0 — caller passes a typed model
trip = Trip(start_date=date(2026, 6, 1), end_date=date(2026, 6, 3),
            display_name="Tokyo", primary_location="Tokyo, JP")
created = client.create_trip(trip)
```

Per-entity methods: `create_<entity>(model)`, `replace_<entity>(id, model)`,
`delete_<entity>(id)` for all 13 object types. They serialize the pydantic
model to XML internally and POST it correctly with OAuth-signed form bodies.

## Errors

```python
# 0.x
result = t.list_trip()
if t.http_code != 200:
    print("oops:", t.response)

# 1.0
from tripit import TripItError, TripItRateLimitError
try:
    trips = list(client.list_trips())
except TripItRateLimitError as e:
    print("rate limited, retry after", e.retry_after)
except TripItError as e:
    print("other failure:", e)
```

Everything raised inherits from `TripItError`. Retryable failures (429, 5xx,
transient network errors) are retried automatically with exponential backoff
inside `_Transport`; you only see them if every retry exhausted.

## Gone with no replacement

- `OAuthConsumerCredential` — split into constructor args + `OAuth1Auth`
  (internal); use `TripIt(...)` directly
- `WebAuthCredential` — TripIt's basic-auth surface was deprecated upstream
- `TravelObj` and its metaclass machinery — replaced by typed pydantic models
- `_parse_command` stack-walking dispatch — replaced by explicit methods
- XML SAX parsing — reads use `?format=json` exclusively
- `t.response` raw-string field — every method returns a typed object
- `t.http_code` — non-2xx becomes a typed exception

If you have 0.x code that touches anything not in this table, open it and
look for the new typed method by name; the surface mirrors the old one
closely.
