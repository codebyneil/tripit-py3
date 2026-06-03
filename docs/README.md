# tripit-py3 docs

## TripIt API v1 schemas

Three XSD files defining the wire contract this library implements:

- `tripit-api-obj-v1.xsd` — every object type (Trip, AirObject, LodgingObject,
  Profile, PointsProgram, etc.). 74 complex types, ~1300 lines. This is the
  authoritative source for the pydantic models under `src/tripit/models/`.
- `tripit-api-req-v1.xsd` — request envelope. Defines what shapes you can POST
  to `/v1/create` and `/v1/replace/<entity>/id/<id>`.
- `tripit-api-res-v1.xsd` — response envelope, including `Error[]` / `Warning[]`
  and pagination fields (`page_num`, `page_size`, `max_page`).

These are copies of the TripIt-published schemas; treat them as read-only. They
are also shipped inside the package (`src/tripit/schemas/`) so the client can
validate generated `<Request>` payloads at runtime. The models bind directly to
these XSDs with `pydantic-xml`.

**Strict by design.** Parsing is strict (`extra="forbid"`): any element or
attribute not in the XSD raises rather than being silently dropped. TripIt does
emit a few out-of-schema fields in the wild (e.g. `Emissions` on `AirSegment`,
`AppleFoundationModel` under `UserSettings`); under strict mode these surface as
loud failures instead of being absorbed, so drift is visible and dealt with
deliberately. `tests/fixtures/xml/air_with_emissions.xml` pins this behavior.

## Coverage & intentional exclusions

Every **trip-data** complexType in `tripit-api-obj-v1.xsd` (65 of 74) has a
typed model. The remaining 9 are **collaboration / request-action** shapes — not
trip data — and are deliberately unmodelled. The client exposes no operation
that sends them, so there is nothing to type:

- `Invitation`, `TripInvitations` — invite people to a trip.
- `TripShare`, `TravelGroupTripShare` — share a trip, or share with a travel group.
- `ConnectionRequest` — request a network connection.
- `TripItemShare`, `EmailMessage` — share a single item / email it.
- `EmailAddresses`, `Addresses` — request-only list containers used only by the
  types above.

`Response`, `Error`, and `Warning` from `tripit-api-res-v1.xsd` are modelled in
`envelope.py`. The split is enforced by
`tests/test_real_fixtures.py::test_every_trip_data_type_is_modeled`.

TripIt's published API documentation lives at
<https://tripit.github.io/api/doc/v1/>. Note TripIt implements OAuth **Core
1.0**, not 1.0a (callback on the authorize redirect; no `oauth_verifier`).
