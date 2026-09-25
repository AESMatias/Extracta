from typing import Any

import pytest
from pydantic import SecretStr

from tests.conftest import ADMIN_PASSWORD, Harness


def users_of(admin: Any, **query: str) -> list[dict[str, Any]]:
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    users: list[dict[str, Any]] = admin.get(f"/api/admin/users?{qs}").get_json()["users"]
    return users


def test_admin_is_disabled_without_a_password(db_engine: object, tmp_path: object) -> None:
    harness = Harness(tmp_path)  # type: ignore[arg-type]
    harness.settings.admin_password = None

    client = harness.client()

    assert client.post("/api/admin/login", json={"password": "anything-long"}).status_code == 404
    assert client.get("/api/admin/session").get_json() == {"enabled": False, "authenticated": False}


def test_admin_login(harness: Harness) -> None:
    client = harness.client()

    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/admin/login", json={"password": "wrong password"}).status_code == 401
    assert client.post("/api/admin/login", json={"password": ADMIN_PASSWORD}).status_code == 200
    assert client.get("/api/admin/session").get_json()["authenticated"] is True
    assert client.get("/api/admin/users").status_code == 200
    client.post("/api/admin/logout")
    assert client.get("/api/admin/users").status_code == 401


def test_admin_password_guessing_is_locked_out(harness: Harness) -> None:
    client = harness.client()
    for _ in range(5):
        client.post("/api/admin/login", json={"password": "guess-guess-guess"})

    assert client.post("/api/admin/login", json={"password": ADMIN_PASSWORD}).status_code == 429


def test_a_user_session_is_not_an_admin_session(harness: Harness) -> None:
    assert harness.signed_up().get("/api/admin/users").status_code == 401


def test_admin_sees_every_account_with_explicit_privileges(harness: Harness) -> None:
    harness.signed_up()
    harness.signed_up("bob@example.com", status="pending")
    admin = harness.admin()

    users = {u["email"]: u for u in users_of(admin)}

    ana = users["ana@example.com"]
    assert ana["status"] == "active"
    assert ana["plan"]["id"] == "free"
    assert ana["privileges"] == {
        "pages": 10,
        "window_hours": 24,
        "max_pages_per_pdf": 10,
        "max_file_mb": 10,
        "max_files_per_upload": 2,
        "can_save_to_db": False,
        "export_formats": ["csv", "xlsx", "json"],
    }
    assert ana["sign_in_methods"] == ["password"]
    assert ana["uploads_24h"] == 0
    assert [u["email"] for u in users_of(admin, status="pending")] == ["bob@example.com"]
    assert [u["email"] for u in users_of(admin, q="bob")] == ["bob@example.com"]


def test_admin_approves_rejects_and_upgrades_accounts(harness: Harness) -> None:
    user_client = harness.signed_up(status="pending")
    admin = harness.admin()
    user_id = users_of(admin)[0]["id"]

    approved = admin.patch(f"/api/admin/users/{user_id}", json={"status": "active"})
    upgraded = admin.patch(
        f"/api/admin/users/{user_id}",
        json={"plan": "business", "plan_expires_at": "2099-01-01T00:00:00Z", "daily_limit_override": 5000},
    )

    assert approved.status_code == 200
    user = upgraded.get_json()["user"]
    assert user["plan"]["id"] == "business"
    assert user["privileges"]["pages"] == 5000  # the override beats the plan's 2,500
    assert user["privileges"]["can_save_to_db"] is True
    me = user_client.get("/api/auth/me").get_json()["user"]
    assert me["plan"]["id"] == "business" and me["page_limit"] == 5000

    admin.patch(f"/api/admin/users/{user_id}", json={"status": "rejected"})
    assert user_client.get("/api/auth/me").get_json()["user"] is None  # rejected accounts are signed out


def test_premium_without_expiry_and_back_to_free(harness: Harness) -> None:
    harness.signed_up()
    admin = harness.admin()
    user_id = users_of(admin)[0]["id"]

    forever = admin.patch(f"/api/admin/users/{user_id}", json={"plan": "ultra", "plan_expires_at": None})
    free = admin.patch(f"/api/admin/users/{user_id}", json={"plan": "free", "daily_limit_override": None})

    assert forever.get_json()["user"]["plan"]["id"] == "ultra"
    assert forever.get_json()["user"]["raw_plan_expires_at"] is None
    assert free.get_json()["user"]["privileges"]["pages"] == 10


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "god"},
        {"plan": "platinum"},
        {"daily_limit_override": -1},
        {"plan_expires_at": "2099-01-01T00:00:00"},  # no timezone
        {"email": "hijack@example.com"},  # not an editable field
    ],
)
def test_admin_updates_are_validated(harness: Harness, payload: dict[str, Any]) -> None:
    harness.signed_up()
    admin = harness.admin()
    user_id = users_of(admin)[0]["id"]

    assert admin.patch(f"/api/admin/users/{user_id}", json=payload).status_code == 400


def test_unknown_users_are_404(harness: Harness) -> None:
    admin = harness.admin()

    assert admin.patch("/api/admin/users/not-a-uuid", json={"status": "active"}).status_code == 404
    assert (
        admin.patch("/api/admin/users/00000000-0000-0000-0000-000000000000", json={"status": "active"}).status_code
        == 404
    )


def test_admin_stats_and_payments(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"pack": "p1000"}).get_json()["order_id"]
    client.post(f"/api/billing/orders/{order_id}/capture")
    admin = harness.admin()

    stats = admin.get("/api/admin/stats").get_json()
    [payment] = admin.get("/api/admin/payments").get_json()["payments"]

    assert stats["users_by_status"] == {"active": 1}
    assert stats["revenue_usd"] == "5.99"
    assert stats["pages_24h"] == 0
    assert payment["email"] == "ana@example.com" and payment["amount"] == "5.99"
    assert (payment["kind"], payment["plan"]) == ("pages", "p1000")
    assert users_of(admin)[0]["paid_total_usd"] == "5.99"
    assert users_of(admin)[0]["page_credits"] == 1000


def test_admin_sets_the_prepaid_page_balance(harness: Harness) -> None:
    client = harness.signed_up()
    admin = harness.admin()
    user_id = users_of(admin)[0]["id"]

    response = admin.patch(f"/api/admin/users/{user_id}", json={"page_credits": 250})

    assert response.status_code == 200 and response.get_json()["user"]["page_credits"] == 250
    assert client.get("/api/auth/me").get_json()["user"]["usage"]["available"] == 260
    assert admin.patch(f"/api/admin/users/{user_id}", json={"page_credits": -5}).status_code == 400


def test_short_admin_password_setting_is_refused() -> None:
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            gemini_api_key=SecretStr("x"),
            database_url=SecretStr("postgresql+psycopg://u:p@h/d"),
            secret_key=SecretStr("k" * 32),
            admin_password=SecretStr("short"),
        )
