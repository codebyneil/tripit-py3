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

These are copies of the TripIt-published schemas; treat them as read-only.
The library's `Response` model in `src/tripit/models/envelope.py` mirrors
`tripit-api-res-v1.xsd`, and `src/tripit/models/objects.py` mirrors the
relevant `complexType` definitions in `tripit-api-obj-v1.xsd`. When the
real captured fixtures surface fields not in the schemas (e.g. `Emissions`,
`AppleFoundationModel`), our models accept them as untyped dicts.

TripIt's published API documentation lives at
<https://tripit.github.io/api/doc/v1/>.
