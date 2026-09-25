"""Email verification, forgot/reset/change password and the sessions they sign out."""

import io
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import session_scope
from app.models import User
from tests.conftest import USER_PASSWORD, Harness, build_pdf

NEW_PASSWORD = "a brand new passphrase"


def register(harness: Harness, email: str = "ana@example.com") -> Any:
    client = harness.client()
    response = client.post("/api/auth/register", json={"email": email, "password": USER_PASSWORD, "name": "Ana"})
    assert response.status_code == 201
    return client


def upload_one(client: Any) -> Any:
    files = [(io.BytesIO(build_pdf(["Invoice number 1 with enough text to read."])), "a.pdf")]
    return client.post("/api/upload", data={"files": files}, content_type="multipart/form-data")


def me(client: Any) -> Any:
    return client.get("/api/auth/me").get_json()["user"]


def login(harness: Harness, password: str, email: str = "ana@example.com") -> Any:
    client = harness.client()
    return client, client.post("/api/auth/login", json={"email": email, "password": password})


# --------------------------------------------------------------------------- email verification


def test_registration_sends_a_verification_link(harness: Harness) -> None:
    client = register(harness)

    email = harness.mailer.last_to("ana@example.com")
    assert "Confirm your email" in email["Subject"]
    assert me(client)["email_verified"] is False
    token = harness.mailer.link_token("ana@example.com")
    assert "http://localhost:8080/verify-email#token=" in str(email.get_body(("plain",)).get_content())  # type: ignore[union-attr]

    response = harness.client().post("/api/auth/email/verify", json={"token": token})  # any browser, no session

    assert response.status_code == 200 and response.get_json() == {"verified": True}
    assert me(client)["email_verified"] is True


def test_unverified_accounts_cannot_upload_or_pay(harness: Harness) -> None:
    client = register(harness)

    refused = upload_one(client)
    assert refused.status_code == 403 and refused.get_json()["verify_email"] is True
    assert client.post("/api/billing/orders", json={"pack": "p100"}).status_code == 403
    assert client.post("/api/billing/subscriptions", json={"plan": "pro"}).status_code == 403

    client.post("/api/auth/email/verify", json={"token": harness.mailer.link_token("ana@example.com")})
    assert upload_one(client).status_code == 202


def test_verification_can_be_turned_off(db_engine: object, tmp_path: Path) -> None:
    harness = Harness(tmp_path, require_email_verification=False)

    assert upload_one(register(harness)).status_code == 202


def test_invalid_verification_links(harness: Harness) -> None:
    register(harness)
    token = harness.mailer.link_token("ana@example.com")
    client = harness.client()

    assert client.post("/api/auth/email/verify", json={"token": "nope"}).status_code == 400
    assert client.post("/api/auth/email/verify", json={}).status_code == 400
    with session_scope() as db:  # the account no longer has the address the link was sent to
        db.execute(select(User)).scalar_one().email = "other@example.com"
    assert client.post("/api/auth/email/verify", json={"token": token}).status_code == 400


def test_resend_verification(harness: Harness) -> None:
    client = register(harness)

    for _ in range(3):
        assert client.post("/api/auth/email/resend").get_json() == {"sent": True}
    assert client.post("/api/auth/email/resend").status_code == 429  # 3 per hour
    assert len(harness.mailer.sent) == 4  # registration + 3 resends

    verified = harness.signed_up("bea@example.com")
    assert verified.post("/api/auth/email/resend").get_json() == {"sent": False, "already_verified": True}
    assert harness.client().post("/api/auth/email/resend").status_code == 401


def test_google_accounts_are_verified(harness: Harness) -> None:
    client = harness.client()
    client.get("/api/auth/google/login")
    client.get(f"/api/auth/google/callback?state={harness.google.last_state}&code=c")

    assert me(client)["email_verified"] is True


def test_linking_google_removes_an_unverified_password(harness: Harness) -> None:
    """Pre-hijacking: an attacker registered the victim's email with a password before the victim."""
    register(harness, "gina@example.com")  # the "attacker", never verified the inbox
    victim = harness.client()
    victim.get("/api/auth/google/login")
    victim.get(f"/api/auth/google/callback?state={harness.google.last_state}&code=c")

    assert me(victim)["email_verified"] is True and me(victim)["has_password"] is False
    assert login(harness, USER_PASSWORD, "gina@example.com")[1].status_code == 401


def test_linking_google_keeps_a_verified_password(harness: Harness) -> None:
    harness.signed_up("gina@example.com")  # verified
    client = harness.client()
    client.get("/api/auth/google/login")
    client.get(f"/api/auth/google/callback?state={harness.google.last_state}&code=c")

    assert me(client)["has_password"] is True
    assert login(harness, USER_PASSWORD, "gina@example.com")[1].status_code == 200


# --------------------------------------------------------------------------- forgot / reset


def test_forgot_password_never_reveals_whether_an_account_exists(harness: Harness) -> None:
    harness.signed_up()
    harness.mailer.sent.clear()
    client = harness.client()

    for email in ("ana@example.com", "nobody@example.com", "not an email"):
        response = client.post("/api/auth/password/forgot", json={"email": email})
        assert (response.status_code, response.get_json()) == (200, {"ok": True})

    assert [m["To"] for m in harness.mailer.sent] == ["ana@example.com"]
    assert "Reset your" in harness.mailer.sent[0]["Subject"]


def test_blocked_accounts_get_no_reset_email(harness: Harness) -> None:
    harness.signed_up(status="suspended")
    harness.mailer.sent.clear()

    harness.client().post("/api/auth/password/forgot", json={"email": "ana@example.com"})

    assert harness.mailer.sent == []


def test_forgot_password_is_rate_limited_per_email(harness: Harness) -> None:
    harness.signed_up()
    client = harness.client()

    codes = [client.post("/api/auth/password/forgot", json={"email": "ana@example.com"}).status_code for _ in range(6)]

    assert codes == [200] * 5 + [429]


def test_reset_password(harness: Harness) -> None:
    old_session = harness.signed_up(verified=False)
    browser = harness.client()
    browser.post("/api/auth/password/forgot", json={"email": "ana@example.com"})
    token = harness.mailer.link_token("ana@example.com")

    response = browser.post("/api/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 200
    user = response.get_json()["user"]
    assert user["email"] == "ana@example.com" and user["email_verified"] is True  # the link proved the inbox
    assert me(browser)["email"] == "ana@example.com"  # signed in right away
    assert me(old_session) is None  # every other session was signed out
    assert login(harness, USER_PASSWORD)[1].status_code == 401
    assert login(harness, NEW_PASSWORD)[1].status_code == 200
    assert "was changed" in harness.mailer.last_to("ana@example.com")["Subject"]
    again = browser.post("/api/auth/password/reset", json={"token": token, "password": "yet another passphrase"})
    assert again.status_code == 400  # each link works once


def test_reset_password_errors(harness: Harness) -> None:
    harness.signed_up()
    client = harness.client()
    client.post("/api/auth/password/forgot", json={"email": "ana@example.com"})
    token = harness.mailer.link_token("ana@example.com")

    assert client.post("/api/auth/password/reset", json={"token": "bad", "password": NEW_PASSWORD}).status_code == 400
    too_short = client.post("/api/auth/password/reset", json={"token": token, "password": "short"})
    assert too_short.status_code == 400 and "between" in too_short.get_json()["error"]
    with session_scope() as db:
        db.execute(select(User)).scalar_one().status = "suspended"
    assert client.post("/api/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}).status_code == 403


# --------------------------------------------------------------------------- change password


def test_change_password_signs_out_other_sessions(harness: Harness) -> None:
    client = harness.signed_up()
    other_session, signed_in = login(harness, USER_PASSWORD)  # the same account on another device
    assert signed_in.status_code == 200 and me(other_session) is not None

    wrong = client.post("/api/auth/password/change", json={"current_password": "wrong", "new_password": NEW_PASSWORD})
    assert wrong.status_code == 401

    changed = client.post(
        "/api/auth/password/change", json={"current_password": USER_PASSWORD, "new_password": NEW_PASSWORD}
    )

    assert changed.status_code == 200, changed.get_json()
    assert me(client) is not None  # this session stays signed in
    assert me(other_session) is None
    assert login(harness, NEW_PASSWORD)[1].status_code == 200
    assert "was changed" in harness.mailer.last_to("ana@example.com")["Subject"]


def test_google_only_accounts_can_add_a_password(harness: Harness) -> None:
    client = harness.client()
    client.get("/api/auth/google/login")
    client.get(f"/api/auth/google/callback?state={harness.google.last_state}&code=c")
    assert me(client)["has_password"] is False

    response = client.post("/api/auth/password/change", json={"new_password": NEW_PASSWORD})

    assert response.status_code == 200 and response.get_json()["user"]["has_password"] is True
    assert login(harness, NEW_PASSWORD, "gina@example.com")[1].status_code == 200


def test_change_password_needs_a_session(harness: Harness) -> None:
    assert harness.client().post("/api/auth/password/change", json={"new_password": NEW_PASSWORD}).status_code == 401


def test_admin_can_mark_an_email_verified(harness: Harness) -> None:
    client = register(harness)
    admin = harness.admin()
    user_id = admin.get("/api/admin/users").get_json()["users"][0]["id"]

    response = admin.patch(f"/api/admin/users/{user_id}", json={"email_verified": True})

    assert response.status_code == 200 and response.get_json()["user"]["email_verified"] is True
    assert me(client)["email_verified"] is True
    admin.patch(f"/api/admin/users/{user_id}", json={"email_verified": False})
    assert me(client)["email_verified"] is False
    with session_scope() as db:
        assert db.execute(select(User)).scalar_one().email_verified_at is None


# --------------------------------------------------------------------------- account deletion


def account_row() -> User:
    with session_scope() as db:
        user = db.execute(select(User)).scalar_one()
        db.expunge(user)
        return user


def test_deleting_my_account_needs_the_password_and_erases_everything(harness: Harness) -> None:
    from app.models import Document, Payment, UsageEvent

    client = harness.signed_up()
    user = account_row()
    with session_scope() as db:
        db.add(UsageEvent(user_id=user.id, task_id=user.id, pages=3))
        db.add(
            Payment(
                user_id=user.id,
                provider_order_id="O1",
                plan="p100",
                pages=100,
                amount=0.99,
                currency="USD",
                status="COMPLETED",
            )
        )

    wrong = client.post("/api/auth/account/delete", json={"password": "not my password"})
    response = client.post("/api/auth/account/delete", json={"password": USER_PASSWORD})

    assert wrong.status_code == 401
    assert response.status_code == 200 and response.get_json() == {"deleted": True}
    assert me(client) is None
    assert login(harness, USER_PASSWORD)[1].status_code == 401
    erased = account_row()
    assert erased.status == "deleted" and erased.email.endswith("@deleted.invalid")
    assert (erased.name, erased.password_hash, erased.google_sub) == (None, None, None)
    with session_scope() as db:
        assert db.query(UsageEvent).count() == 0 and db.query(Document).count() == 0
        assert db.query(Payment).count() == 1  # kept for tax law, with no personal data left
    assert "was deleted" in harness.mailer.last_to("ana@example.com")["Subject"]


def test_google_only_accounts_confirm_with_their_email(harness: Harness) -> None:
    client = harness.client()
    client.get("/api/auth/google/login")
    client.get(f"/api/auth/google/callback?state={harness.google.last_state}&code=c")

    assert client.post("/api/auth/account/delete", json={"email": "someone@else.com"}).status_code == 400
    assert client.post("/api/auth/account/delete", json={"email": "Gina@Example.com"}).status_code == 200


def test_deleting_by_email_link(harness: Harness) -> None:
    harness.signed_up()
    anyone = harness.client()
    harness.mailer.sent.clear()

    for email in ("nobody@example.com", "not an email"):
        assert anyone.post("/api/auth/account/delete-request", json={"email": email}).get_json() == {"ok": True}
    assert harness.mailer.sent == []
    anyone.post("/api/auth/account/delete-request", json={"email": "ana@example.com"})
    assert "Confirm the deletion" in harness.mailer.last_to("ana@example.com")["Subject"]
    token = harness.mailer.link_token("ana@example.com")

    assert anyone.post("/api/auth/account/delete-confirm", json={"token": "bad"}).status_code == 400
    assert anyone.post("/api/auth/account/delete-confirm", json={"token": token}).get_json() == {"deleted": True}
    assert account_row().status == "deleted"
    assert anyone.post("/api/auth/account/delete-confirm", json={"token": token}).status_code == 400  # once


def test_deleted_accounts_cannot_use_their_old_session(harness: Harness) -> None:
    client = harness.signed_up()
    other_device = login(harness, USER_PASSWORD)[0]

    response = client.post("/api/auth/account/delete", json={"password": USER_PASSWORD})

    assert response.status_code == 200, response.get_json()
    assert me(other_device) is None


# --------------------------------------------------------------------------- deletion requests in /admin


def deletion_requests(harness: Harness) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = harness.admin().get("/api/admin/deletion-requests").get_json()["requests"]
    return requests


class BrokenMailer:
    def send(self, message: object) -> None:
        raise ConnectionRefusedError("no SMTP server")


def test_form_requests_reach_the_admin_even_when_the_email_fails(harness: Harness) -> None:
    harness.signed_up()
    harness.app.extensions["mailer"] = BrokenMailer()
    anyone = harness.client()

    for email in ("ana@example.com", "ANA@example.com", "nobody@example.com"):
        assert anyone.post("/api/auth/account/delete-request", json={"email": email}).get_json() == {"ok": True}

    [request] = deletion_requests(harness)  # the repeat updates the pending one; unknown emails add nothing
    assert (request["email"], request["name"], request["status"], request["account_status"]) == (
        "ana@example.com",
        "Ana",
        "pending",
        "active",
    )
    assert harness.admin().get("/api/admin/stats").get_json()["pending_deletions"] == 1


def test_the_admin_completes_a_deletion_request(harness: Harness) -> None:
    harness.signed_up()
    harness.client().post("/api/auth/account/delete-request", json={"email": "ana@example.com"})
    [request] = deletion_requests(harness)
    admin = harness.admin()

    response = admin.post(f"/api/admin/deletion-requests/{request['id']}/complete")

    assert response.status_code == 200
    done = response.get_json()["request"]
    assert (done["status"], done["account_status"], done["email"]) == ("completed", "deleted", "ana@example.com")
    assert done["resolved_at"] is not None
    assert account_row().status == "deleted"
    assert "was deleted" in harness.mailer.last_to("ana@example.com")["Subject"]
    assert admin.post(f"/api/admin/deletion-requests/{request['id']}/complete").status_code == 409
    assert admin.get("/api/admin/stats").get_json()["pending_deletions"] == 0


def test_the_admin_dismisses_a_deletion_request(harness: Harness) -> None:
    harness.signed_up()
    harness.client().post("/api/auth/account/delete-request", json={"email": "ana@example.com"})
    [request] = deletion_requests(harness)
    admin = harness.admin()

    response = admin.post(f"/api/admin/deletion-requests/{request['id']}/dismiss")

    assert response.get_json()["request"]["status"] == "dismissed"
    assert account_row().status == "active"
    assert admin.post(f"/api/admin/deletion-requests/{request['id']}/dismiss").status_code == 409
    for bad in ("not-a-uuid", "00000000-0000-0000-0000-000000000000"):
        assert admin.post(f"/api/admin/deletion-requests/{bad}/dismiss").status_code == 404


def test_confirming_by_link_closes_the_request(harness: Harness) -> None:
    harness.signed_up()
    anyone = harness.client()
    anyone.post("/api/auth/account/delete-request", json={"email": "ana@example.com"})

    anyone.post("/api/auth/account/delete-confirm", json={"token": harness.mailer.link_token("ana@example.com")})

    [request] = deletion_requests(harness)
    assert request["status"] == "completed"


def test_the_admin_deletes_an_account_directly(harness: Harness) -> None:
    harness.signed_up()
    user = account_row()
    admin = harness.admin()

    assert harness.client().post(f"/api/admin/users/{user.id}/delete").status_code == 401
    assert admin.post(f"/api/admin/users/{user.id}/delete").get_json() == {"deleted": True}
    assert account_row().status == "deleted"
    assert admin.post(f"/api/admin/users/{user.id}/delete").status_code == 404  # already gone
    assert admin.post("/api/admin/users/nope/delete").status_code == 404
    assert harness.client().get("/api/admin/deletion-requests").status_code == 401
