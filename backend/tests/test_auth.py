"""Auth token signing/verification."""

from app.api.auth_token import make_token, parse_token


def test_token_roundtrip():
    token = make_token("maya@parcelpilot.com")
    assert parse_token(token) == "maya@parcelpilot.com"


def test_token_is_case_normalised():
    assert parse_token(make_token("Maya@ParcelPilot.com")) == "maya@parcelpilot.com"


def test_tampered_token_rejected():
    token = make_token("maya@parcelpilot.com")
    # Flip a character in the payload; signature must no longer match.
    tampered = ("A" if token[0] != "A" else "B") + token[1:]
    assert parse_token(tampered) != "maya@parcelpilot.com"


def test_garbage_token_returns_none():
    assert parse_token("not-a-real-token") is None
