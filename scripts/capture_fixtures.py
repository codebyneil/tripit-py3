"""Capture live TripIt API responses, scrub them, write fixtures.

Usage:
    uv run python scripts/capture_fixtures.py             # capture everything available
    uv run python scripts/capture_fixtures.py --only trip # restrict by category
    uv run python scripts/capture_fixtures.py --refresh-oauth  # re-do the OAuth dance

Reads credentials from `tripit_creds.json` (or env vars). On first run, walks
the user through a one-time browser-based OAuth approval; subsequent runs
reuse the cached access token.

Writes one JSON file per endpoint to `tests/fixtures/json/real_*.json`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Allow direct `python scripts/capture_fixtures.py` invocation by ensuring the
# repo root is on sys.path before we import `scripts._capture.*`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts._capture.credentials import (  # noqa: E402
    MissingCredentialsError,
    load_credentials,
)
from scripts._capture.endpoints import discovery_pass, iter_capture_specs  # noqa: E402
from scripts._capture.oauth_setup import (  # noqa: E402
    OAuthApprovalRequired,
    ensure_access_token,
)
from scripts._capture.scrub import scrub  # noqa: E402
from scripts._capture.tokens import clear_tokens, load_tokens  # noqa: E402
from tripit import TripIt  # noqa: E402

FIXTURES_DIR = Path("tests/fixtures/json")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="capture_fixtures",
        description="Capture live TripIt API responses for use as test fixtures.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=["profile", "points", "trip", "object", "list_object"],
        default=None,
        help="Restrict capture to one or more categories (repeatable).",
    )
    parser.add_argument(
        "--refresh-oauth",
        action="store_true",
        help="Discard the cached access token and re-run the OAuth handshake.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and print the capture plan without hitting endpoints.",
    )
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)
    log = logging.getLogger("tripit.capture")

    try:
        creds = load_credentials()
    except MissingCredentialsError as exc:
        log.error("%s", exc)
        return 1

    tokens = clear_tokens() if args.refresh_oauth else load_tokens()

    try:
        tokens, _ = ensure_access_token(creds, tokens, force=args.refresh_oauth)
    except OAuthApprovalRequired as need:
        # Print friendly instructions on stdout, exit 0 so the user can
        # clearly see what to do next.
        sys.stdout.write(
            "\n"
            "OAuth approval required — TripIt's Akamai bot detection blocks\n"
            "scripted login. Complete the dance manually:\n\n"
            f"  1. Open this URL in your browser:\n     {need.auth_url}\n\n"
            "  2. Click 'Approve' on the TripIt page.\n"
            "  3. Re-run this command. The script will exchange the\n"
            "     approved request token for an access token and capture.\n\n"
            "The request token is saved in tripit_tokens.json. The URL above\n"
            "is reused on subsequent runs until you approve it — so if you\n"
            "lose the URL, just re-run and you'll see it again.\n"
        )
        if need.reason != "fresh approval required":
            sys.stdout.write(f"\n(reason: {need.reason})\n")
        return 0
    except Exception as exc:
        log.error("OAuth handshake failed: %s", exc)
        return 2

    only = set(args.only) if args.only else None

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    with TripIt(
        consumer_key=creds.consumer_key,
        consumer_secret=creds.consumer_secret,
        token=tokens.access_token or "",
        token_secret=tokens.access_token_secret or "",
    ) as client:
        log.info("Running discovery pass...")
        disc = discovery_pass(client)
        log.info(
            "Discovery: %d trip(s), %d points program(s), object types: %s",
            len(disc.trip_ids),
            len(disc.points_program_ids),
            sorted(t for t, ids in disc.object_ids_by_type.items() if ids),
        )

        specs = list(iter_capture_specs(disc, only=only))
        log.info("Capture plan: %d endpoints", len(specs))

        if args.dry_run:
            for spec in specs:
                qs = "&".join(f"{k}={v}" for k, v in spec.params.items())
                qs_suffix = f"?{qs}" if qs else ""
                print(f"{spec.filename}\t<- {spec.method} {spec.path}{qs_suffix}")
            return 0

        captured = 0
        for spec in specs:
            log.info("Capturing %s", spec.filename)
            try:
                raw = client._transport.request_raw(
                    spec.method, spec.path, params=spec.params or None
                )
            except Exception as exc:
                log.warning("  ↳ failed: %s", exc)
                continue
            clean = scrub(raw)
            out_path = FIXTURES_DIR / spec.filename
            out_path.write_text(json.dumps(clean, indent=2, sort_keys=True) + "\n")
            captured += 1

        log.info("Wrote %d fixture file(s) to %s", captured, FIXTURES_DIR)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
