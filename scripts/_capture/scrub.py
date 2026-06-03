"""Deterministic light-touch PII scrubbing for captured TripIt responses.

Per the plan: only obvious PII (names, emails, phone numbers, street
addresses) is redacted. City/state/country/lat-lon, dates, IDs, airport
codes, trip names, notes, and booking codes are all preserved — they're
the load-bearing signal for the round-trip + unknown-fields tests.

Determinism: the same input value always scrubs to the same fake value.
Implementation uses sha256-derived suffixes so cross-references are
preserved within and across fixture files (same email in multiple fixtures
scrubs identically).
"""

from __future__ import annotations

import hashlib
from typing import Any

from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs

# Lowercase field names whose value should be replaced.
_NAME_FIELDS = frozenset(
    {
        "first_name",
        "middle_name",
        "last_name",
        "screen_name",
        "public_display_name",
        "cal_user_display_name",
        "agency_client_name",
        "agency_contact",
    }
)
_EMAIL_FIELDS = frozenset(
    {
        "sms_email_address",
        "supplier_email_address",
        "booking_site_email_address",
        "agency_email_address",
    }
)
_PHONE_FIELDS = frozenset(
    {
        "sms_phone_number",
        "supplier_phone",
        "booking_site_phone",
        "agency_phone",
        "start_location_phone",
        "end_location_phone",
        "location_phone",
    }
)
_STREET_FIELDS = frozenset({"addr1", "addr2"})


def _fake(kind: str, real: str) -> str:
    """Map (kind, real) → stable fake value using sha256."""
    suffix = hashlib.sha256(f"{kind}:{real}".encode()).hexdigest()[:8]
    match kind:
        case "name":
            return f"Person {suffix}"
        case "email":
            return f"{suffix}@example.invalid"
        case "phone":
            return f"+1-555-555-{suffix[:4]}"
        case "street":
            return f"{int(suffix, 16) % 9000 + 100} {suffix} Street"
    return suffix


def _scrub_email_record(record: dict[str, Any]) -> dict[str, Any]:
    """A ProfileEmailAddress block — the `address` field is the email."""
    out = dict(record)
    if isinstance(out.get("address"), str):
        out["address"] = _fake("email", out["address"])
    return out


def _looks_like_email_record(record: dict[str, Any]) -> bool:
    """Detect a ProfileEmailAddress-like dict by structural sibling keys."""
    return "address" in record and any(
        k in record for k in ("is_auto_import", "is_confirmed", "is_primary", "uuid_ref")
    )


def scrub(data: Any) -> Any:
    """Return a deep-copied, scrubbed version of `data`.

    Walks dicts/lists recursively; rewrites the value of any key in the
    redaction sets above; otherwise passes through unchanged.
    """
    if isinstance(data, dict):
        if _looks_like_email_record(data):
            data = _scrub_email_record(data)
        out: dict[str, Any] = {}
        for key, value in data.items():
            lk = key.lower() if isinstance(key, str) else key
            if isinstance(value, str):
                if lk in _NAME_FIELDS:
                    out[key] = _fake("name", value)
                    continue
                if lk in _EMAIL_FIELDS:
                    out[key] = _fake("email", value)
                    continue
                if lk in _PHONE_FIELDS:
                    out[key] = _fake("phone", value)
                    continue
                if lk in _STREET_FIELDS:
                    out[key] = _fake("street", value)
                    continue
            out[key] = scrub(value)
        return out
    if isinstance(data, list):
        return [scrub(item) for item in data]
    return data


def scrub_xml(xml_text: str) -> str:
    """Scrub a captured XML response string, reusing the same field heuristics.

    Walks the element tree and rewrites the text of any element whose tag is a
    redaction field (by lowercased tag name). An `<address>` element is treated
    as an email only when it sits inside a `ProfileEmailAddress` (matching the
    dict scrubber's structural rule).
    """
    root = etree.fromstring(xml_text.encode("utf-8"))
    for el in root.iter():
        text = el.text
        if not isinstance(text, str) or not text.strip():
            continue
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        if tag in _NAME_FIELDS:
            el.text = _fake("name", text)
        elif tag in _EMAIL_FIELDS:
            el.text = _fake("email", text)
        elif tag in _PHONE_FIELDS:
            el.text = _fake("phone", text)
        elif tag in _STREET_FIELDS:
            el.text = _fake("street", text)
        elif tag == "address":
            parent = el.getparent()
            if parent is not None and parent.tag == "ProfileEmailAddress":
                el.text = _fake("email", text)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")
