"""XML (de)serialization helpers built on pydantic-xml + lxml.

Reads parse straight into the `Response` model via pydantic-xml. Writes wrap a
single object model into the `<Request>` envelope TripIt expects on
`/v1/create` and `/v1/replace/<entity>`.

Validation against the shipped XSDs is **asymmetric** (see plan):

- Requests are validated by default — we generate them, the request schema is a
  simple choice with no referential constraints, so enforcing conformance is
  cheap and catches our own bugs early.
- Responses are *not* validated by default — the response schema is an ordered
  sequence with `xs:key`/`xs:keyref` integrity (Invitee→Profile) that valid
  partial TripIt payloads don't satisfy. `validate_response_xml` is available for
  opt-in conformance runs.
"""

from __future__ import annotations

import functools
from pathlib import Path

from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs
from pydantic_xml import BaseXmlModel

from tripit.exceptions import TripItValidationError

_SCHEMA_DIR = Path(__file__).parent / "schemas"
_REQUEST_XSD = _SCHEMA_DIR / "tripit-api-req-v1.xsd"
_RESPONSE_XSD = _SCHEMA_DIR / "tripit-api-res-v1.xsd"


@functools.lru_cache(maxsize=2)
def _schema(path: Path) -> etree.XMLSchema:
    # Parse from the on-disk path so the schema's relative `xs:include` of
    # tripit-api-obj-v1.xsd resolves (works the same from a site-packages
    # install, since the schemas ship inside the package).
    return etree.XMLSchema(etree.parse(str(path)))


def build_request_xml(tag: str, model: BaseXmlModel) -> str:
    """Wrap one object model in a `<Request>` envelope and return XML text.

    `tag` is the XSD element name the object is bound to (e.g. ``"AirObject"``).
    The payload is validated against the request schema before being returned;
    a schema violation raises `TripItValidationError`.
    """
    inner = model.to_xml_tree(skip_empty=True)
    inner.tag = tag
    request = etree.Element("Request")
    request.append(inner)
    validate_request_tree(request)
    return etree.tostring(request, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def validate_request_tree(tree: etree._Element) -> None:
    """Validate a `<Request>` element tree against the request XSD."""
    schema = _schema(_REQUEST_XSD)
    if not schema.validate(tree):
        raise TripItValidationError(f"request failed XSD validation: {schema.error_log!s}")


def validate_response_xml(payload: bytes) -> None:
    """Validate raw response bytes against the response XSD (opt-in).

    Tolerant callers should expect this to reject legitimate partial responses
    (ordering + Invitee/Profile keyref); use it for conformance checks, not the
    hot path.
    """
    schema = _schema(_RESPONSE_XSD)
    doc = etree.fromstring(payload)
    if not schema.validate(doc):
        raise TripItValidationError(f"response failed XSD validation: {schema.error_log!s}")
