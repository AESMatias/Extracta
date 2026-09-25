from app.db import session_scope
from app.models import Payment, User
from tests.conftest import Harness


def buy(client: object, pack: str = "p1000") -> tuple[str, object]:
    order_id: str = client.post("/api/billing/orders", json={"pack": pack}).get_json()["order_id"]  # type: ignore[attr-defined]
    return order_id, client.post(f"/api/billing/orders/{order_id}/capture")  # type: ignore[attr-defined]


def credits(client: object) -> int:
    return int(client.get("/api/auth/me").get_json()["user"]["page_credits"])  # type: ignore[attr-defined]


def test_catalog_is_public(harness: Harness) -> None:
    catalog = harness.client().get("/api/plans").get_json()

    assert [p["id"] for p in catalog["plans"]] == ["free", "starter", "pro", "business", "ultra"]
    assert catalog["plans"][2]["price_usd"] == "4.99" and catalog["plans"][2]["highlight"] is True
    assert [p["pages"] for p in catalog["packs"]] == [100, 250, 500, 1000, 2500, 5000]
    assert catalog["packs"][3] == {"id": "p1000", "pages": 1000, "price_usd": "5.99", "price_per_page": "0.0060"}


def test_billing_config(harness: Harness) -> None:
    assert harness.client().get("/api/billing/config").get_json() == {
        "enabled": True,
        "client_id": "paypal-client-id",
        "currency": "USD",
        "env": "sandbox",
    }
    harness.app.extensions["paypal"] = None
    assert harness.client().get("/api/billing/config").get_json() == {"enabled": False}


def test_orders_need_an_account_and_a_real_pack(harness: Harness) -> None:
    assert harness.client().post("/api/billing/orders", json={"pack": "p100"}).status_code == 401
    assert harness.signed_up().post("/api/billing/orders", json={"pack": "p7"}).status_code == 400
    assert harness.signed_up("bob@example.com").post("/api/billing/orders", json={"plan": "pro"}).status_code == 400


def test_buying_a_pack_adds_prepaid_pages(harness: Harness) -> None:
    client = harness.signed_up()

    order_id, response = buy(client, "p1000")

    assert response.status_code == 200  # type: ignore[attr-defined]
    user = response.get_json()["user"]  # type: ignore[attr-defined]
    assert user["page_credits"] == 1000 and user["usage"]["available"] == 1010
    assert user["plan"]["id"] == "free"  # packs do not change the plan
    order = harness.paypal.orders[order_id]["purchase_units"][0]
    assert order["amount"] == {"currency_code": "USD", "value": "5.99"}  # price decided by the server
    assert order["custom_id"].endswith(":pack:p1000")
    with session_scope() as db:
        payment = db.query(Payment).one()
        assert (payment.kind, payment.plan, payment.pages, str(payment.amount)) == ("pages", "p1000", 1000, "5.99")
        assert payment.provider_capture_id == f"CAP-{order_id}"
    assert client.get("/api/billing/payments").get_json()["payments"][0]["pages"] == 1000


def test_packs_add_up(harness: Harness) -> None:
    client = harness.signed_up()
    buy(client, "p100")
    buy(client, "p250")

    assert credits(client) == 350


def test_capturing_twice_charges_once(harness: Harness) -> None:
    client = harness.signed_up()
    order_id, _ = buy(client)

    again = client.post(f"/api/billing/orders/{order_id}/capture")

    assert again.status_code == 200
    assert harness.paypal.captured == [order_id]
    assert credits(client) == 1000
    with session_scope() as db:
        assert db.query(Payment).count() == 1


def test_packs_can_be_bought_with_an_active_subscription(harness: Harness) -> None:
    from datetime import timedelta

    from app.db import utcnow

    client = harness.signed_up(plan="pro", plan_expires_at=utcnow() + timedelta(days=20))

    _, response = buy(client, "p500")

    assert response.status_code == 200  # type: ignore[attr-defined]
    assert credits(client) == 500


def test_someone_elses_order_cannot_be_captured(harness: Harness) -> None:
    order_id = harness.signed_up().post("/api/billing/orders", json={"pack": "p100"}).get_json()["order_id"]
    thief = harness.signed_up("eve@example.com")

    response = thief.post(f"/api/billing/orders/{order_id}/capture")

    assert response.status_code == 404
    assert harness.paypal.captured == []


def test_tampered_amount_or_pack_is_refused_before_capturing(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"pack": "p5000"}).get_json()["order_id"]
    harness.paypal.orders[order_id]["purchase_units"][0]["amount"]["value"] = "0.01"
    assert client.post(f"/api/billing/orders/{order_id}/capture").status_code == 400

    other = client.post("/api/billing/orders", json={"pack": "p100"}).get_json()["order_id"]
    unit = harness.paypal.orders[other]["purchase_units"][0]
    unit["custom_id"] = unit["custom_id"].replace("p100", "p9999")
    assert client.post(f"/api/billing/orders/{other}/capture").status_code == 404
    assert harness.paypal.captured == []


def test_incomplete_payment_adds_nothing(harness: Harness) -> None:
    client = harness.signed_up()
    harness.paypal.capture_status = "PENDING"

    _, response = buy(client)

    assert response.status_code == 402  # type: ignore[attr-defined]
    assert credits(client) == 0


def test_paypal_outage_and_missing_configuration(harness: Harness) -> None:
    client = harness.signed_up()
    harness.paypal.fail = True
    assert client.post("/api/billing/orders", json={"pack": "p100"}).status_code == 502
    harness.app.extensions["paypal"] = None
    assert client.post("/api/billing/orders", json={"pack": "p100"}).status_code == 503
    assert client.post("/api/billing/orders/ORDER1/capture").status_code == 503
    with session_scope() as db:
        assert db.query(User).one().page_credits == 0
