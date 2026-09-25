import time
import uuid

import pytest
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.timed import TimestampSigner

from app import tokens
from app.models import User

SECRET = "s" * 32


def user(password_hash: str | None = "hash-1") -> User:
    return User(id=uuid.uuid4(), email="ana@example.com", password_hash=password_hash)


def later(monkeypatch: pytest.MonkeyPatch, seconds: int) -> None:
    """Make itsdangerous believe `seconds` have passed since the token was signed."""
    now = int(time.time()) + seconds
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: now)


def test_email_verification_round_trip() -> None:
    account = user()

    user_id, email = tokens.read_email_verification_token(SECRET, tokens.email_verification_token(SECRET, account))

    assert (user_id, email) == (account.id, "ana@example.com")


@pytest.mark.parametrize(
    "token",
    ["", "garbage", "eyJ1IjoiMSJ9.tampered.signature"],
)
def test_malformed_or_tampered_tokens_are_refused(token: str) -> None:
    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, token)


def test_a_token_signed_with_another_secret_is_refused() -> None:
    token = tokens.email_verification_token("x" * 32, user())

    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, token)


def test_tokens_cannot_be_used_for_the_other_purpose() -> None:
    account = user()

    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, tokens.password_reset_token(SECRET, account))
    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_password_reset_token(SECRET, tokens.email_verification_token(SECRET, account))


def test_verification_links_expire_after_three_days(monkeypatch: pytest.MonkeyPatch) -> None:
    token = tokens.email_verification_token(SECRET, user())

    later(monkeypatch, 3 * 24 * 3600 - 60)
    tokens.read_email_verification_token(SECRET, token)
    later(monkeypatch, 3 * 24 * 3600 + 60)
    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, token)


def test_reset_links_expire_after_one_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    token = tokens.password_reset_token(SECRET, user())

    later(monkeypatch, 3600 + 60)
    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_password_reset_token(SECRET, token)


def test_reset_token_carries_the_password_fingerprint() -> None:
    account = user("hash-1")
    _, fingerprint = tokens.read_password_reset_token(SECRET, tokens.password_reset_token(SECRET, account))

    assert fingerprint == tokens.password_fingerprint(account)
    account.password_hash = "hash-2"  # the password changed: the old link no longer matches
    assert fingerprint != tokens.password_fingerprint(account)


def test_fingerprint_changes_when_a_google_account_adds_a_password() -> None:
    account = user(None)
    before = tokens.password_fingerprint(account)
    account.password_hash = "hash"

    assert before != tokens.password_fingerprint(account)


def test_payloads_that_are_not_objects_or_lack_a_valid_id_are_refused() -> None:
    signer = URLSafeTimedSerializer(SECRET, salt="extracta.verify-email")

    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, signer.dumps("just a string"))
    with pytest.raises(tokens.InvalidTokenError):
        tokens.read_email_verification_token(SECRET, signer.dumps({"u": "not-a-uuid", "e": "a@b.co"}))
