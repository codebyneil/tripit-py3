"""Walk the 3-legged TripIt OAuth 1.0a flow from a terminal.

    $ tripit-authorize --consumer-key K --consumer-secret S

Prints the access token + secret you can plug into `TripIt(...)`. Reads the
consumer key/secret from CLI flags, the environment (`TRIPIT_CONSUMER_KEY` /
`TRIPIT_CONSUMER_SECRET`), or an interactive prompt — in that order.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TextIO

from tripit.auth import (
    DEFAULT_API_URL,
    authorization_url,
    get_access_token,
    get_request_token,
)
from tripit.exceptions import TripItError


def _resolve(value: str | None, env_var: str, prompt: str, stream: TextIO) -> str:
    if value:
        return value
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env
    stream.write(f"{prompt}: ")
    stream.flush()
    line = sys.stdin.readline().strip()
    if not line:
        raise SystemExit(f"{env_var} required.")
    return line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tripit-authorize",
        description="Walk the 3-legged TripIt OAuth 1.0a flow and print access tokens.",
    )
    parser.add_argument("--consumer-key", help="TripIt API consumer key.")
    parser.add_argument("--consumer-secret", help="TripIt API consumer secret.")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Override the TripIt API base URL (default: production).",
    )
    parser.add_argument(
        "--web-url",
        default="https://www.tripit.com",
        help="Override the TripIt web base URL used for the authorize step.",
    )
    parser.add_argument(
        "--callback-url",
        default=None,
        help="Optional OAuth callback URL. If omitted, the user authorizes "
        "out-of-band and the script waits on a keypress.",
    )
    args = parser.parse_args(argv)

    out = sys.stderr  # keep stdout clean for the final tokens
    try:
        consumer_key = _resolve(args.consumer_key, "TRIPIT_CONSUMER_KEY", "Consumer key", out)
        consumer_secret = _resolve(
            args.consumer_secret, "TRIPIT_CONSUMER_SECRET", "Consumer secret", out
        )

        out.write("\nFetching request token...\n")
        out.flush()
        request_token = get_request_token(consumer_key, consumer_secret, api_url=args.api_url)

        auth_url = authorization_url(
            request_token.oauth_token,
            callback_url=args.callback_url,
            web_url=args.web_url,
        )
        out.write("\nOpen this URL in a browser and approve access:\n\n")
        out.write(f"  {auth_url}\n\n")
        out.write("After approving, press Enter to continue...")
        out.flush()
        sys.stdin.readline()

        out.write("\nExchanging for access token...\n")
        out.flush()
        access_token = get_access_token(
            consumer_key,
            consumer_secret,
            request_token.oauth_token,
            request_token.oauth_token_secret,
            api_url=args.api_url,
        )

        sys.stdout.write(
            "\nSuccess. Save these credentials and pass them to TripIt():\n\n"
            f"  token        = {access_token.oauth_token}\n"
            f"  token_secret = {access_token.oauth_token_secret}\n"
        )
        return 0
    except TripItError as exc:
        out.write(f"\nError: {exc}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
