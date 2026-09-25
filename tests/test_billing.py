from datetime import datetime, timedelta

from app.db import session_scope, utcnow
from app.models import Payment, User
from tests.conftest import Harness


def buy(client: object, plan: str = "pro") -> tuple[str, object]:
    order_id: str = client.post("/api/billing/orders", json={"plan": plan}).get_json()["order_id"]  # type: ignore[attr-defined]
    return order_id, client.post(f"/api/billing/orders/{order_id}/capture")  # type: ignore[attr-defined]


def test_plans_are_public(harness: Harness) -> None:
    plans = harness.client().get("/api/plans").get_json()["plans"]

    assert [p["id"] for p in plans] == ["free", "starter", "pro", "business", "ultra"]
    assert plans[2]["price_usd"] == "4.99" and plans[2]["highlight"] is True


def test_billing_config(harness: Harness) -> None:
    assert harness.client().get("/api/billing/config").get_json() == {
        "enabled": True,
        "client_id": "paypal-client-id",
        "currency": "USD",
        "env": "sandbox",
    }
    harness.app.extensions["paypal"] = None
    assert harness.client().get("/api/billing/config").get_json() == {"enabled": False}


def test_orders_need_an_account_and_a_paid_plan(harness: Harness) -> None:
    assert harness.client().post("/api/billing/orders", json={"plan": "pro"}).status_code == 401
    assert harness.signed_up().post("/api/billing/orders", json={"plan": "free"}).status_code == 400


def test_buying_a_plan_upgrades_the_account_for_30_days(harness: Harness) -> None:
    client = harness.signed_up()

    order_id, response = buy(client, "pro")

    assert response.status_code == 200  # type: ignore[attr-defined]
    user = response.get_json()["user"]  # type: ignore[attr-defined]
    assert user["plan"]["id"] == "pro"
    assert user["usage"]["limit"] == 100
    expires = datetime.fromisoformat(user["plan_expires_at"])
    assert timedelta(days=29, hours=23) < expires - utcnow() <= timedelta(days=30)
    order = harness.paypal.orders[order_id]["purchase_units"][0]
    assert order["amount"] == {"currency_code": "USD", "value": "4.99"}  # price decided by the server
    with session_scope() as db:
        payment = db.query(Payment).one()
        assert (payment.plan, str(payment.amount), payment.status) == ("pro", "4.99", "COMPLETED")
    assert client.get("/api/billing/payments").get_json()["payments"][0]["amount"] == "4.99"


def test_capturing_twice_charges_once(harness: Harness) -> None:
    client = harness.signed_up()
    order_id, _ = buy(client)

    again = client.post(f"/api/billing/orders/{order_id}/capture")

    assert again.status_code == 200
    assert harness.paypal.captured == [order_id]
    with session_scope() as db:
        assert db.query(Payment).count() == 1


def test_buying_the_same_plan_again_extends_it(harness: Harness) -> None:
    client = harness.signed_up()
    buy(client)
    with session_scope() as db:
        first_expiry = db.query(User).one().plan_expires_at

    _, response = buy(client)

    second_expiry = datetime.fromisoformat(response.get_json()["user"]["plan_expires_at"])  # type: ignore[attr-defined]
    assert first_expiry is not None
    assert second_expiry - first_expiry == timedelta(days=30)


def test_someone_elses_order_cannot_be_captured(harness: Harness) -> None:
    order_id = harness.signed_up().post("/api/billing/orders", json={"plan": "pro"}).get_json()["order_id"]
    thief = harness.signed_up("eve@example.com")

    response = thief.post(f"/api/billing/orders/{order_id}/capture")

    assert response.status_code == 404
    assert harness.paypal.captured == []


def test_tampered_amount_is_refused_before_capturing(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"plan": "ultra"}).get_json()["order_id"]
    harness.paypal.orders[order_id]["purchase_units"][0]["amount"]["value"] = "0.01"

    response = client.post(f"/api/billing/orders/{order_id}/capture")

    assert response.status_code == 400
    assert harness.paypal.captured == []


def test_incomplete_payment_does_not_upgrade(harness: Harness) -> None:
    client = harness.signed_up()
    harness.paypal.capture_status = "PENDING"

    _, response = buy(client)

    assert response.status_code == 402  # type: ignore[attr-defined]
    assert client.get("/api/auth/me").get_json()["user"]["plan"]["id"] == "free"


def test_paypal_outage_and_missing_configuration(harness: Harness) -> None:
    client = harness.signed_up()
    harness.paypal.fail = True
    assert client.post("/api/billing/orders", json={"plan": "pro"}).status_code == 502
    harness.app.extensions["paypal"] = None
    assert client.post("/api/billing/orders", json={"plan": "pro"}).status_code == 503
    assert client.post("/api/billing/orders/ORDER1/capture").status_code == 503
