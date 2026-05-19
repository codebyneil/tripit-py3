"""Best-effort programmatic OAuth approval against tripit.com.

`approve_request_token(creds, request_token)` tries to:
  1. Log into www.tripit.com with the user's username/password
  2. Visit /oauth/authorize?oauth_token=<rt>
  3. Submit the approval form

Returns True on success, False on any failure. **Never raises** — failures
are logged with a single-line reason code so the orchestrator can fall back
cleanly to the manual approval UI.

This is dev-only tooling and inherently fragile (TripIt's web pages are not
part of the documented API surface). If a step starts failing, the manual
fallback in oauth_setup.py is the safety net.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag  # ty: ignore[unresolved-import]

from scripts._capture.credentials import Credentials

logger = logging.getLogger("tripit.capture.login")

# Browser-like UA — TripIt's web pages sometimes serve a JS-only fallback to
# non-browser UAs.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)

_CAPTCHA_MARKERS = (
    "recaptcha",
    "g-recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "verify your identity",
    "are you a robot",
    "security check",
)
_LOGIN_FAIL_MARKERS = (
    "incorrect",
    "invalid",
    "could not log in",
    "couldn't sign in",
)


def _is_likely_login_page(html: str, url: str) -> bool:
    """Heuristic: does this look like the login form rather than a logged-in page?"""
    if "/account/login" in url:
        return True
    lower = html.lower()
    return 'name="password"' in lower and 'name="username"' in lower


def _detect_captcha(html: str) -> bool:
    lower = html.lower()
    return any(marker in lower for marker in _CAPTCHA_MARKERS)


def _detect_login_failure(html: str) -> bool:
    lower = html.lower()
    return any(marker in lower for marker in _LOGIN_FAIL_MARKERS)


def _extract_form(html: str, action_must_contain: str | None = None) -> dict | None:
    """Find the first form whose action matches the constraint and pull all inputs.

    Returns {"action": <absolute_or_relative_url>, "method": "POST", "fields": {...}}
    or None if no matching form is found.
    """
    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        if not isinstance(form, Tag):
            continue
        action = form.get("action", "") or ""
        if action_must_contain and action_must_contain not in str(action):
            continue
        method = str(form.get("method", "POST")).upper()
        fields: dict[str, str] = {}
        for el in form.find_all(("input", "button")):
            if not isinstance(el, Tag):
                continue
            name = el.get("name")
            if not name:
                continue
            value = el.get("value", "")
            fields[str(name)] = str(value)
        return {"action": str(action), "method": method, "fields": fields}
    return None


def _find_approve_button(html: str) -> tuple[str, str] | None:
    """Locate the (name, value) of the form's approve submit button."""
    soup = BeautifulSoup(html, "html.parser")
    for el in soup.find_all(("input", "button")):
        if not isinstance(el, Tag):
            continue
        kind = (el.get("type") or "").lower()
        if kind not in ("submit", "button", ""):
            continue
        value = str(el.get("value") or el.get_text(strip=True) or "")
        name = el.get("name")
        if value and re.search(r"approve|allow|authorize|grant", value, re.I):
            return (str(name) if name else "submit", value)
    return None


def approve_request_token(
    creds: Credentials,
    request_token: str,
    *,
    web_url: str = "https://www.tripit.com",
) -> bool:
    """Try to authorize `request_token` against tripit.com using creds.username/password.

    Returns True iff the request token has been authorized by the user; False
    on any failure (logged with a reason code).
    """
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": _UA},
        ) as c:
            if not _login(c, creds, web_url):
                return False
            return _authorize_request_token(c, request_token, web_url)
    except httpx.HTTPError as exc:
        logger.warning("programmatic login: network error: %s", exc)
        return False


def _login(client: httpx.Client, creds: Credentials, web_url: str) -> bool:
    login_url = f"{web_url}/account/login"
    try:
        page = client.get(login_url)
    except httpx.HTTPError as exc:
        logger.warning("login: GET %s failed: %s", login_url, exc)
        return False

    if page.status_code >= 400:
        logger.warning("login: GET returned %d", page.status_code)
        return False

    if _detect_captcha(page.text):
        logger.warning("login: captcha detected on login page — falling back to manual")
        return False

    form = _extract_form(page.text, action_must_contain="login")
    if form is None:
        logger.warning("login: form not found on login page")
        return False

    fields = dict(form["fields"])
    # Detect username and password fields by partial-name match. TripIt's
    # form names them `login_email_address` and `login_password`; the regex
    # is permissive so a future rename doesn't immediately break us.
    user_field = next(
        (
            k
            for k in fields
            if re.search(r"(email|user|login)", k, re.I) and "password" not in k.lower()
        ),
        None,
    )
    pass_field = next(
        (k for k in fields if re.search(r"password|passwd", k, re.I)),
        None,
    )
    if user_field is None or pass_field is None:
        logger.warning(
            "login: could not identify username/password fields among %s",
            sorted(fields.keys()),
        )
        return False
    fields[user_field] = creds.username
    fields[pass_field] = creds.password

    action = urljoin(login_url, form["action"]) if form["action"] else login_url
    try:
        resp = client.request(form["method"], action, data=fields)
    except httpx.HTTPError as exc:
        logger.warning("login: POST failed: %s", exc)
        return False

    if resp.status_code in (401, 403):
        # Distinguish credential rejection from Akamai/edge bot blocking.
        body_lower = resp.text.lower()
        if "access denied" in body_lower or "errors.edgesuite.net" in body_lower:
            logger.warning(
                "login: %d — Akamai bot manager blocked the request; manual approval required",
                resp.status_code,
            )
        else:
            logger.warning("login: %d — credentials rejected", resp.status_code)
        return False
    if resp.status_code == 429:
        logger.warning("login: 429 — rate limited")
        return False
    if _detect_captcha(resp.text):
        logger.warning("login: captcha challenge after submitting credentials")
        return False
    if _detect_login_failure(resp.text) and _is_likely_login_page(resp.text, str(resp.url)):
        logger.warning("login: still on login page with error markers")
        return False
    if _is_likely_login_page(resp.text, str(resp.url)):
        logger.warning("login: post-submit URL still looks like login (cookies dropped?)")
        return False
    return True


def _authorize_request_token(client: httpx.Client, request_token: str, web_url: str) -> bool:
    authorize_url = f"{web_url}/oauth/authorize?oauth_token={request_token}"
    try:
        page = client.get(authorize_url)
    except httpx.HTTPError as exc:
        logger.warning("authorize: GET failed: %s", exc)
        return False

    if page.status_code >= 400:
        logger.warning("authorize: GET returned %d", page.status_code)
        return False
    if _is_likely_login_page(page.text, str(page.url)):
        logger.warning("authorize: redirected back to login (session not preserved)")
        return False
    if _detect_captcha(page.text):
        logger.warning("authorize: captcha on approval page")
        return False

    form = _extract_form(page.text, action_must_contain="authorize")
    if form is None:
        # Some OAuth approval flows auto-approve when the consumer is already
        # trusted — there's no form to submit. If the page indicates success,
        # we can return True.
        lower = page.text.lower()
        if any(s in lower for s in ("successfully", "you may now close", "authorized")):
            logger.info("authorize: auto-approved (no form)")
            return True
        logger.warning("authorize: approval form not found on page")
        return False

    approve = _find_approve_button(page.text)
    fields = dict(form["fields"])
    if approve is not None:
        approve_name, approve_value = approve
        fields[approve_name] = approve_value

    action = urljoin(authorize_url, form["action"]) if form["action"] else authorize_url
    try:
        resp = client.request(form["method"], action, data=fields)
    except httpx.HTTPError as exc:
        logger.warning("authorize: POST failed: %s", exc)
        return False

    if resp.status_code >= 400:
        logger.warning("authorize: POST returned %d", resp.status_code)
        return False

    lower = resp.text.lower()
    if any(s in lower for s in ("successfully", "you may now close", "authorized", "complete")):
        logger.info("authorize: success markers present")
        return True

    # Some flows just redirect to the callback or a generic confirmation —
    # treat 2xx without explicit failure markers as success.
    if not _is_likely_login_page(resp.text, str(resp.url)) and not _detect_captcha(resp.text):
        logger.info("authorize: 2xx with no failure markers — assuming success")
        return True

    logger.warning("authorize: post-submit page didn't indicate success")
    return False
