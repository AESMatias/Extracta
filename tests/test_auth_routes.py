from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select

from app.db import session_scope
from app.models import User
from tests.conftest import USER_PASSWORD, Harness


def test_register_signs_the_browser_in(harness: Harness) -> None:
    client = harness.client()

    response = client.post(
        "/api/auth/register", json={"email": "Ana@Example.com", "password": USER_PASSWORD, "name": "Ana"}
    )

    assert response.status_code == 201
    user = response.get_json()["user"]
    assert user["email"] == "ana@example.com"
    assert user["status"] == "active"
    assert user["plan"]["id"] == "free"
    assert user["usage"] == {
        "used": 0,
        "limit": 10,
        "remaining": 10,
        "credits": 0,
        "available": 10,
        "window_hours": 24,
        "next_slot_at": None,
    }
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert client.get("/api/auth/me").get_json()["user"]["email"] == "ana@example.com"


def test_register_rejects_duplicates_and_weak_passwords(harness: Harness) -> None:
    harness.signed_up()
    client = harness.client()

    duplicate = client.post("/api/auth/register", json={"email": "ana@example.com", "password": USER_PASSWORD})
    weak = client.post("/api/auth/register", json={"email": "bob@example.com", "password": "123"})
    not_json = client.post("/api/auth/register", data="x", content_type="text/plain")

    assert duplicate.status_code == 409
    assert weak.status_code == 400
    assert not_json.status_code == 400


def test_registration_is_rate_limited_per_ip(harness: Harness) -> None:
    client = harness.client()
    codes = [
        client.post("/api/auth/register", json={"email": f"u{i}@example.com", "password": USER_PASSWORD}).status_code
        for i in range(11)
    ]

    assert codes[:10] == [201] * 10
    assert codes[10] == 429


def test_login_and_logout(harness: Harness) -> None:
    harness.signed_up()
    client = harness.client()

    wrong = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "not the password"})
    right = client.post("/api/auth/login", json={"email": "ANA@example.com", "password": USER_PASSWORD})
    me = client.get("/api/auth/me")
    client.post("/api/auth/logout")

    assert wrong.status_code == 401
    assert wrong.get_json()["error"] == "Incorrect email or password."
    assert right.status_code == 200
    assert me.get_json()["user"]["email"] == "ana@example.com"
    assert client.get("/api/auth/me").get_json()["user"] is None


def test_login_is_rate_limited_per_account(harness: Harness) -> None:
    harness.signed_up()
    client = harness.client()
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "ana@example.com", "password": "guess guess guess"})

    blocked = client.post("/api/auth/login", json={"email": "ana@example.com", "password": USER_PASSWORD})

    assert blocked.status_code == 429  # even the right password waits once the account is under attack
    assert blocked.get_json()["challenge_required"] is True


def test_three_layer_login_defense_bot_drop_known_device_and_pow(harness: Harness) -> None:
    import hashlib

    from app.web.security import _has_leading_zero_bits, create_pow_challenge

    owner = harness.signed_up()
    owner.post("/api/auth/logout")  # logs out, but keeps the known-device marker in the cookie

    bot = harness.client()
    bot_res = bot.post(
        "/api/auth/login",
        json={"email": "ana@example.com", "password": USER_PASSWORD},
        headers={"User-Agent": "python-requests/2.32.0"},
    )
    assert bot_res.status_code == 429

    # Overlong (> 256 bytes) passwords are rejected in Layer 3 without running 600k PBKDF2 rounds.
    overlong = harness.client().post(
        "/api/auth/login",
        json={"email": "ana@example.com", "password": "X" * 400},
    )
    assert overlong.status_code == 401

    # Attacker floods ana@example.com with 10 failed attempts from a different IP.
    attacker = harness.client()
    for _ in range(10):
        attacker.post(
            "/api/auth/login",
            json={"email": "ana@example.com", "password": "wrong password"},
            environ_base={"REMOTE_ADDR": "198.51.100.77"},
        )

    # Known device (owner) is NOT globally locked out by the attacker's flood.
    owner_login = owner.post("/api/auth/login", json={"email": "ana@example.com", "password": USER_PASSWORD})
    assert owner_login.status_code == 200

    # New unknown browser receives a PoW challenge and signs in after solving it.
    new_browser = harness.client()
    challenged = new_browser.post(
        "/api/auth/login",
        json={"email": "ana@example.com", "password": USER_PASSWORD},
        environ_base={"REMOTE_ADDR": "203.0.113.55"},
        headers={"User-Agent": "Mozilla/5.0 TestBrowser"},
    )
    assert challenged.status_code == 429
    assert challenged.get_json()["challenge_required"] is True

    challenge = create_pow_challenge("k" * 32, "203.0.113.55", "Mozilla/5.0 TestBrowser", bits=10)
    nonce = "0"
    for idx in range(200_000):
        candidate = format(idx, "x")
        digest = hashlib.sha256(f"{challenge}:{candidate}".encode()).digest()
        if _has_leading_zero_bits(digest, 10):
            nonce = candidate
            break
    solved = new_browser.post(
        "/api/auth/login",
        json={
            "email": "ana@example.com",
            "password": USER_PASSWORD,
            "pow_challenge": challenge,
            "pow_nonce": nonce,
        },
        environ_base={"REMOTE_ADDR": "203.0.113.55"},
        headers={"User-Agent": "Mozilla/5.0 TestBrowser"},
    )
    assert solved.status_code == 200


def test_suspending_an_account_ends_its_sessions(harness: Harness) -> None:
    client = harness.signed_up()
    with session_scope() as db:
        db.execute(select(User)).scalar_one().status = "suspended"

    assert client.get("/api/auth/me").get_json()["user"] is None


def test_manual_approval_mode(db_engine: object, tmp_path: object) -> None:
    harness = Harness(tmp_path, require_manual_approval=True)  # type: ignore[arg-type]

    response = harness.client().post("/api/auth/register", json={"email": "ana@example.com", "password": USER_PASSWORD})

    assert response.get_json()["user"]["status"] == "pending"
    providers = harness.client().get("/api/auth/providers").get_json()
    assert providers == {"google": False, "manual_approval": True, "email_verification": True}


# --------------------------------------------------------------------------- Google


def test_google_sign_in_round_trip(harness: Harness) -> None:
    client = harness.client()

    start = client.get("/api/auth/google/login")
    state = parse_qs(urlsplit(start.headers["Location"]).query)["state"][0]
    callback = client.get(f"/api/auth/google/callback?state={state}&code=abc")

    assert start.status_code == 302 and start.headers["Location"].startswith("https://accounts.google.com/")
    assert callback.status_code == 302
    assert callback.headers["Location"] == "http://localhost:8080/app"
    me = client.get("/api/auth/me").get_json()["user"]
    assert me["email"] == "gina@example.com"
    assert me["has_google"] is True and me["has_password"] is False


def test_google_callback_with_a_forged_state_is_refused(harness: Harness) -> None:
    client = harness.client()
    client.get("/api/auth/google/login")

    callback = client.get("/api/auth/google/callback?state=forged&code=abc")

    assert callback.headers["Location"] == "http://localhost:8080/login?error=google_cancelled"
    assert client.get("/api/auth/me").get_json()["user"] is None


def test_google_failure_and_blocked_accounts_return_to_login(harness: Harness) -> None:
    harness.google.fail = True
    client = harness.client()
    state = parse_qs(urlsplit(client.get("/api/auth/google/login").headers["Location"]).query)["state"][0]

    failed = client.get(f"/api/auth/google/callback?state={state}&code=abc")

    assert failed.headers["Location"].endswith("/login?error=google_failed")


def test_google_is_404_when_not_configured(db_engine: object, tmp_path: object) -> None:
    harness = Harness(tmp_path)  # type: ignore[arg-type]
    harness.app.extensions["google"] = None

    assert harness.client().get("/api/auth/google/login").status_code == 404
