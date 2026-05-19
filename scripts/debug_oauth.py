"""Verbose, single-pass diagnostic for the TripIt OAuth 1.0 dance.

Run this when the regular capture script can't get an access token. It will:

  1. Sign a POST to /oauth/request_token and print the exact Authorization
     header, request body, response status, and response body.
  2. Build the authorize URL and fetch it ourselves to see what TripIt
     thinks about the token. If we see "Access Request Failed" / Akamai
     here, the issue is server-side (the token is being rejected before
     the user ever clicks).
  3. Print the authorize URL for the user to visit.

Does NOT touch tripit_tokens.json — this is read-only diagnostic.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx  # noqa: E402

from scripts._capture.credentials import load_credentials  # noqa: E402
from tripit.auth import OAuth1Auth, authorization_url  # noqa: E402


def main() -> int:
    creds = load_credentials()

    print("=" * 72)
    print("[1] System clock vs unix epoch")
    print(f"    time.time() = {time.time():.3f}")
    print("    NB: TripIt rejects timestamps drifted by more than ±3 hours from server time.")

    print()
    print("=" * 72)
    print("[2] POST https://api.tripit.com/oauth/request_token (no oauth_callback)")
    auth = OAuth1Auth(creds.consumer_key, creds.consumer_secret)
    request = httpx.Request("POST", "https://api.tripit.com/oauth/request_token")
    auth_header = auth._build_header(request)
    print(f"    Authorization: {auth_header}")
    with httpx.Client(timeout=30.0) as c:
        resp = c.post("https://api.tripit.com/oauth/request_token", auth=auth)
    print(f"    -> HTTP {resp.status_code}")
    for k, v in resp.headers.items():
        print(f"    {k}: {v}")
    print("    --- body ---")
    print(f"    {resp.text!r}")

    if resp.status_code != 200 or "oauth_token=" not in resp.text:
        print("\n!! request_token call did not produce a usable token; aborting.")
        return 1

    # Parse body
    from urllib.parse import parse_qsl

    body = dict(parse_qsl(resp.text))
    rt = body["oauth_token"]
    rt_secret = body["oauth_token_secret"]
    print(f"\n    parsed: oauth_token={rt!r} (len={len(rt)})")
    print(f"            oauth_token_secret=<{len(rt_secret)} chars>")

    print()
    print("=" * 72)
    print("[3] Retry with oauth_callback=oob (some 1.0a servers require it)")
    auth_cb = OAuth1Auth(creds.consumer_key, creds.consumer_secret)
    req_cb = httpx.Request(
        "POST",
        "https://api.tripit.com/oauth/request_token",
        content=b"oauth_callback=oob",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    cb_header = auth_cb._build_header(req_cb)
    print(f"    Authorization: {cb_header}")
    with httpx.Client(timeout=30.0) as c:
        resp_cb = c.post(
            "https://api.tripit.com/oauth/request_token",
            content=b"oauth_callback=oob",
            headers={"content-type": "application/x-www-form-urlencoded"},
            auth=auth_cb,
        )
    print(f"    -> HTTP {resp_cb.status_code}")
    print(f"    body: {resp_cb.text!r}")

    rt_cb = None
    if resp_cb.status_code == 200 and "oauth_token=" in resp_cb.text:
        cb_body = dict(parse_qsl(resp_cb.text))
        rt_cb = cb_body.get("oauth_token")
        print(
            f"    parsed: oauth_token={rt_cb!r}   callback_confirmed="
            f"{cb_body.get('oauth_callback_confirmed')!r}"
        )

    print()
    print("=" * 72)
    print("[4] Fetch the authorize page directly (without user login) to see")
    print("    what TripIt says about the token.")
    auth_url = authorization_url(rt)
    print(f"    URL: {auth_url}")
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Safari/605.1.15"
    )
    with httpx.Client(follow_redirects=True, headers={"User-Agent": UA}) as c:
        page = c.get(auth_url)
    print(f"    -> HTTP {page.status_code}")
    print(f"    Final URL: {page.url}")
    print(f"    Content-Length: {len(page.text)}")
    snippets = []
    for needle in (
        "access request failed",
        "you may now close",
        "successfully authorized",
        "access denied",
        "errors.edgesuite.net",
        "<title>",
        "incorrect",
        "invalid",
        "please log",
    ):
        idx = page.text.lower().find(needle)
        if idx >= 0:
            window = page.text[max(0, idx - 40) : idx + 120]
            snippets.append(f"    found {needle!r} at {idx}: ...{window!r}...")
    if snippets:
        print("    body markers:")
        for s in snippets:
            print(s)
    else:
        print("    (no diagnostic markers found in body)")

    print()
    print("=" * 72)
    print("[5] Summary")
    print(f"    Plain POST: oauth_token={rt!r}")
    if rt_cb:
        print(f"    With oob callback: oauth_token={rt_cb!r}")
    print()
    print("    AUTHORIZE URLS (click both; report which one — if either — works):")
    print(f"      A. {authorization_url(rt)}")
    if rt_cb and rt_cb != rt:
        print(f"      B. {authorization_url(rt_cb)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
