"""Dump all of a TripIt account's trip data to a single JSON file.

Different from `capture_fixtures.py`:
- One output file, not a fixture-per-endpoint matrix.
- No scrubbing — output is the user's own data, preserved verbatim.
- Includes the full envelope for both upcoming and past trips with all
  nested objects, plus profile + points programs.

The API speaks XML; to preserve verbatim fidelity (including any out-of-schema
elements that strict parsing would reject) the raw XML payloads are embedded as
strings inside the JSON wrapper.

Usage:
    uv run python scripts/export_trips.py
    uv run python scripts/export_trips.py --output ~/Desktop/trips-backup.json
    uv run python scripts/export_trips.py --pretty
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
from pathlib import Path

from lxml import etree  # ty: ignore[unresolved-import]  # lxml has no PEP 561 stubs

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts._capture.credentials import (  # noqa: E402
    MissingCredentialsError,
    load_credentials,
)
from scripts._capture.oauth_setup import (  # noqa: E402
    OAuthApprovalRequired,
    ensure_access_token,
)
from scripts._capture.tokens import clear_tokens, load_tokens  # noqa: E402
from tripit import TripIt  # noqa: E402

logger = logging.getLogger("tripit.export")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export_trips",
        description="Dump all of a TripIt account's trip data to a single JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("tripit_export.json"),
        help="Path to write the dump to (default: tripit_export.json).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON output for human readability.",
    )
    parser.add_argument(
        "--refresh-oauth",
        action="store_true",
        help="Re-run the OAuth handshake (defaults to using cached tokens).",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=8765,
        help="Port for the OAuth callback listener (default 8765).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=25,
        help="TripIt list page size (default 25, max 25).",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging.")
    return parser.parse_args(argv)


def _paginate_raw(client: TripIt, path: str, base_params: dict[str, str]) -> list[str]:
    """Fetch every page of a list endpoint, returning the raw XML page bodies."""
    pages: list[str] = []
    page = 1
    while True:
        params = {**base_params, "page_num": str(page)}
        raw = client._transport.request_raw("GET", path, params=params)
        pages.append(raw)
        root = etree.fromstring(raw.encode("utf-8"))
        max_page_text = root.findtext("max_page")
        max_page = int(max_page_text) if max_page_text and max_page_text.isdigit() else None
        if max_page is None or page >= max_page:
            return pages
        page += 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        creds = load_credentials()
    except MissingCredentialsError as exc:
        logger.error("%s", exc)
        return 1

    tokens = clear_tokens() if args.refresh_oauth else load_tokens()
    try:
        tokens, _ = ensure_access_token(
            creds, tokens, force=args.refresh_oauth, listen_port=args.listen_port
        )
    except OAuthApprovalRequired as need:
        sys.stdout.write(
            f"\nOAuth approval required. Open this URL, approve, then re-run:\n  {need.auth_url}\n"
        )
        return 0
    except Exception as exc:
        logger.error("OAuth handshake failed: %s", exc)
        return 2

    page_size = str(min(args.page_size, 25))

    with TripIt(
        consumer_key=creds.consumer_key,
        consumer_secret=creds.consumer_secret,
        token=tokens.access_token or "",
        token_secret=tokens.access_token_secret or "",
    ) as client:
        logger.info("Fetching profile...")
        profile_raw = client._transport.request_raw("GET", "/v1/get/profile")

        logger.info("Fetching points programs...")
        points_raw = client._transport.request_raw("GET", "/v1/list/points_program")

        logger.info("Fetching upcoming trips...")
        upcoming_pages = _paginate_raw(
            client,
            "/v1/list/trip",
            {"include_objects": "true", "page_size": page_size},
        )

        logger.info("Fetching past trips...")
        past_pages = _paginate_raw(
            client,
            "/v1/list/trip",
            {"past": "true", "include_objects": "true", "page_size": page_size},
        )

    payload = {
        "exported_at": _dt.datetime.now(_dt.UTC).isoformat(),
        "consumer_key": creds.consumer_key,
        "profile_xml": profile_raw,
        "points_programs_xml": points_raw,
        "trips_upcoming_xml": upcoming_pages,
        "trips_past_xml": past_pages,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        if args.pretty:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        else:
            json.dump(payload, f)

    n_upcoming = sum(_count_trips(p) for p in upcoming_pages)
    n_past = sum(_count_trips(p) for p in past_pages)
    logger.info(
        "Wrote %s: %d upcoming trip(s), %d past trip(s), %.1f KB",
        args.output,
        n_upcoming,
        n_past,
        args.output.stat().st_size / 1024,
    )
    return 0


def _count_trips(xml_page: str) -> int:
    """Count <Trip> elements in a raw XML page body."""
    root = etree.fromstring(xml_page.encode("utf-8"))
    return len(root.findall("Trip"))


if __name__ == "__main__":
    raise SystemExit(main())
