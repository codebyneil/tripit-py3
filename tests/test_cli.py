"""Tests for the tripit-authorize CLI."""

from __future__ import annotations

import io
import sys
from collections.abc import Iterator

import httpx
import pytest
import respx

from tripit.cli.authorize import main


@pytest.fixture
def stdin_lines() -> Iterator[list[str]]:
    """Replace sys.stdin with a buffer that returns the given lines in order."""
    original = sys.stdin
    buf = io.StringIO()
    sys.stdin = buf
    yield buf  # tests can write to buf before triggering reads
    sys.stdin = original


@respx.mock
def test_authorize_happy_path_prints_access_token(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate the user pressing Enter at the wait prompt.
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n"))

    respx.post("https://api.tripit.com/oauth/request_token").mock(
        return_value=httpx.Response(200, text="oauth_token=rt-1&oauth_token_secret=rs-1")
    )
    respx.post("https://api.tripit.com/oauth/access_token").mock(
        return_value=httpx.Response(200, text="oauth_token=at-2&oauth_token_secret=as-2")
    )

    rc = main(["--consumer-key", "K", "--consumer-secret", "S"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "token        = at-2" in captured.out
    assert "token_secret = as-2" in captured.out
    # The authorization URL is shown to the user on stderr.
    assert "oauth_token=rt-1" in captured.err
    assert "https://www.tripit.com/oauth/authorize" in captured.err


@respx.mock
def test_authorize_propagates_failure_as_nonzero_exit(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n"))
    respx.post("https://api.tripit.com/oauth/request_token").mock(
        return_value=httpx.Response(401, text="bad signature")
    )

    rc = main(["--consumer-key", "K", "--consumer-secret", "S"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "Error:" in captured.err
