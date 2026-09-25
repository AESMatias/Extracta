"""Monthly subscriptions, PayPal webhooks and the periodic reconciliation (fake PayPal)."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from app import billing
from app.db import session_scope, utcnow
from app.models import Payment, PayPalPlan, Subscription, User, WebhookEvent
from tests.conftest import Harness

WEBHOOK_ID = "WH-TEST"


@pytest.fixture
def harness(db_engine: object, tmp_path: Path) -> Harness:
    return Harness(tmp_path, paypal_webhook_id=WEBHOOK_ID)


def subscribe(client: Any, plan: str = "pro") -> str:
    response = client.post("/api/billing/subscriptions", json={"plan": plan})
    assert response.status_code == 201, response.get_json()
    return str(response.get_json()["subscription_id"])


def active(harness: Harness, client: Any, plan: str = "pro", days: int = 30) -> tuple[str, datetime]:
    """Subscribe, let the buyer approve it in PayPal, and activate it."""
    subscription_id = subscribe(client, plan)
    next_billing = (utcnow() + timedelta(days=days)).replace(microsecond=0)
    harness.paypal.set_subscription(subscription_id, "ACTIVE", next_billing)
    assert client.post(f"/api/billing/subscriptions/{subscription_id}/activate").status_code == 200
    return subscription_id, next_billing


def account(email: str = "ana@example.com") -> User:
    with session_scope() as db:
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        db.expunge(user)
        return user


def webhook(harness: Harness, event_type: str, resource: dict[str, Any], event_id: str = "WH-EVENT-1") -> Any:
    body = json.dumps({"id": event_id, "event_type": event_type, "resource": resource})
    return harness.client().post("/api/billing/webhook", data=body, content_type="application/json")


# --------------------------------------------------------------------------- subscribing


def test_subscribing_creates_the_paypal_plan_once(harness: Harness) -> None:
    subscription_id = subscribe(harness.signed_up())
    subscribe(harness.signed_up("bea@example.com"))

    created = harness.paypal.subscriptions[subscription_id]
    assert created["custom_id"] == f"{account().id}:pro"
    assert created["start_time"] is None
    assert len(harness.paypal.products) == 1 and len(harness.paypal.billing_plans) == 1  # reused
    with session_scope() as db:
        row = db.execute(select(PayPalPlan)).scalar_one()
        assert (row.env, row.plan, str(row.price)) == ("sandbox", "pro", "4.99")
        assert db.execute(select(Subscription)).scalars().first().status == "APPROVAL_PENDING"  # type: ignore[union-attr]


def test_each_plan_and_price_gets_its_own_paypal_plan(harness: Harness) -> None:
    subscribe(harness.signed_up(), "pro")
    subscribe(harness.signed_up("bea@example.com"), "starter")

    assert sorted(p.id for p in harness.paypal.billing_plans.values()) == ["pro", "starter"]
    assert len(harness.paypal.products) == 1  # one product for every plan


def test_activating_applies_the_plan_until_the_next_billing_date_plus_grace(harness: Harness) -> None:
    client = harness.signed_up()

    subscription_id, next_billing = active(harness, client)

    user = client.get("/api/auth/me").get_json()["user"]
    assert user["plan"]["id"] == "pro" and user["usage"]["limit"] == 1000
    assert datetime.fromisoformat(user["plan_expires_at"]) == next_billing + billing.GRACE
    assert user["subscription"] == {
        "id": subscription_id,
        "plan": "pro",
        "status": "ACTIVE",
        "next_billing_at": next_billing.isoformat(),
        "cancelled_at": None,
    }


def test_activation_waits_while_paypal_is_still_charging(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id = subscribe(client)
    harness.paypal.set_subscription(subscription_id, "APPROVED")

    response = client.post(f"/api/billing/subscriptions/{subscription_id}/activate")

    assert response.status_code == 202 and response.get_json()["status"] == "APPROVED"
    assert response.get_json()["user"]["plan"]["id"] == "free"


def test_nobody_can_activate_someone_elses_subscription(harness: Harness) -> None:
    subscription_id = subscribe(harness.signed_up())
    harness.paypal.set_subscription(subscription_id, "ACTIVE", utcnow() + timedelta(days=30))
    eve = harness.signed_up("eve@example.com")

    assert eve.post(f"/api/billing/subscriptions/{subscription_id}/activate").status_code == 404
    assert eve.get("/api/auth/me").get_json()["user"]["plan"]["id"] == "free"


def test_a_subscription_to_a_plan_not_created_here_is_refused(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id = subscribe(client)
    harness.paypal.subscriptions[subscription_id]["plan_id"] = "P-SOMEONE-ELSES-PLAN"
    harness.paypal.set_subscription(subscription_id, "ACTIVE", utcnow() + timedelta(days=30))

    assert client.post(f"/api/billing/subscriptions/{subscription_id}/activate").status_code == 404


def test_a_tampered_plan_in_custom_id_is_refused(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id = subscribe(client, "starter")
    data = harness.paypal.subscriptions[subscription_id]
    data["custom_id"] = data["custom_id"].replace(":starter", ":ultra")  # the paid plan is still Starter
    harness.paypal.set_subscription(subscription_id, "ACTIVE", utcnow() + timedelta(days=30))

    assert client.post(f"/api/billing/subscriptions/{subscription_id}/activate").status_code == 404


def test_one_subscription_at_a_time(harness: Harness) -> None:
    client = harness.signed_up()
    active(harness, client)

    response = client.post("/api/billing/subscriptions", json={"plan": "business"})

    assert response.status_code == 409 and "Cancel it first" in response.get_json()["error"]


def test_an_abandoned_checkout_does_not_block_a_new_one(harness: Harness) -> None:
    client = harness.signed_up()
    subscribe(client)  # the buyer closed PayPal's window

    assert client.get("/api/auth/me").get_json()["user"]["subscription"] is None
    subscribe(client)


def test_subscribing_to_the_plan_of_a_prepaid_pass_starts_billing_when_it_ends(harness: Harness) -> None:
    expires = (utcnow() + timedelta(days=12)).replace(microsecond=0)
    client = harness.signed_up(plan="pro", plan_expires_at=expires)

    subscription_id = subscribe(client, "pro")

    assert harness.paypal.subscriptions[subscription_id]["start_time"] == expires
    harness.paypal.set_subscription(subscription_id, "ACTIVE", expires)  # first charge on that date
    client.post(f"/api/billing/subscriptions/{subscription_id}/activate")
    user = client.get("/api/auth/me").get_json()["user"]
    assert datetime.fromisoformat(user["plan_expires_at"]) == expires + billing.GRACE


def test_subscribing_needs_a_paid_plan_and_payments_configured(harness: Harness) -> None:
    client = harness.signed_up()
    assert client.post("/api/billing/subscriptions", json={"plan": "free"}).status_code == 400
    harness.paypal.fail = True
    assert client.post("/api/billing/subscriptions", json={"plan": "pro"}).status_code == 502
    harness.app.extensions["paypal"] = None
    assert client.post("/api/billing/subscriptions", json={"plan": "pro"}).status_code == 503
    assert client.post("/api/billing/subscriptions/bad!id/activate").status_code == 503


def test_invalid_subscription_ids(harness: Harness) -> None:
    client = harness.signed_up()

    assert client.post("/api/billing/subscriptions/bad!id/activate").status_code == 400
    assert client.post(f"/api/billing/subscriptions/{'x' * 65}/activate").status_code == 400


# --------------------------------------------------------------------------- cancelling


def test_cancelling_keeps_the_plan_until_the_paid_period_ends(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, next_billing = active(harness, client)

    response = client.post("/api/billing/subscription/cancel")

    assert response.status_code == 200
    user = response.get_json()["user"]
    assert harness.paypal.cancelled == [subscription_id]
    assert user["plan"]["id"] == "pro"
    assert datetime.fromisoformat(user["plan_expires_at"]) == next_billing  # the grace days are gone
    assert user["subscription"]["status"] == "CANCELLED" and user["subscription"]["cancelled_at"]
    subscribe(client, "business")  # a cancelled subscription no longer blocks a new one


def test_cancelling_without_a_subscription(harness: Harness) -> None:
    client = harness.signed_up()

    assert client.post("/api/billing/subscription/cancel").status_code == 404
    harness.paypal.fail = True
    active_client = harness.signed_up("bea@example.com")
    assert active_client.post("/api/billing/subscription/cancel").status_code == 404


def test_paypal_outage_while_cancelling(harness: Harness) -> None:
    client = harness.signed_up()
    active(harness, client)
    harness.paypal.fail = True

    assert client.post("/api/billing/subscription/cancel").status_code == 502
    assert client.get("/api/auth/me").get_json()["user"]["subscription"]["status"] == "ACTIVE"


# --------------------------------------------------------------------------- webhooks


def test_webhooks_need_configuration_and_a_valid_signature(db_engine: object, tmp_path: Path) -> None:
    unconfigured = Harness(tmp_path)
    assert webhook(unconfigured, "PAYMENT.SALE.COMPLETED", {}).status_code == 503

    harness = Harness(tmp_path, paypal_webhook_id=WEBHOOK_ID)
    harness.paypal.webhook_valid = False
    assert webhook(harness, "PAYMENT.SALE.COMPLETED", {}).status_code == 400
    with session_scope() as db:
        assert db.execute(select(WebhookEvent)).first() is None


def test_webhook_body_is_forwarded_as_received(harness: Harness) -> None:
    raw = '{"id":"WH-1",  "event_type":"SOMETHING.ELSE","resource":{}}'  # odd spacing on purpose

    response = harness.client().post("/api/billing/webhook", data=raw, content_type="application/json")

    assert response.get_json() == {"result": "processed"}
    assert harness.paypal.verified_bodies == [raw]


def test_renewal_payment_extends_the_plan_and_is_recorded_once(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    renewed_until = (utcnow() + timedelta(days=60)).replace(microsecond=0)
    harness.paypal.set_subscription(subscription_id, "ACTIVE", renewed_until)
    sale = {"id": "SALE-1", "billing_agreement_id": subscription_id, "amount": {"total": "4.99", "currency": "USD"}}

    first = webhook(harness, "PAYMENT.SALE.COMPLETED", sale)
    again = webhook(harness, "PAYMENT.SALE.COMPLETED", sale)  # PayPal redelivers
    another_event = webhook(harness, "PAYMENT.SALE.COMPLETED", sale, event_id="WH-EVENT-2")

    assert first.get_json() == {"result": "processed"}
    assert again.get_json() == {"result": "duplicate"}
    assert another_event.status_code == 200
    user = client.get("/api/auth/me").get_json()["user"]
    assert datetime.fromisoformat(user["plan_expires_at"]) == renewed_until + billing.GRACE
    with session_scope() as db:
        [payment] = db.execute(select(Payment)).scalars().all()
        assert (payment.kind, payment.provider_order_id, str(payment.amount)) == ("subscription", "SALE-1", "4.99")
        assert payment.subscription_id is not None
    payments = client.get("/api/billing/payments").get_json()["payments"]
    assert payments[0]["kind"] == "subscription"


def test_sales_without_a_subscription_are_ignored(harness: Harness) -> None:
    assert webhook(harness, "PAYMENT.SALE.COMPLETED", {"id": "SALE-9"}).get_json() == {"result": "processed"}
    with session_scope() as db:
        assert db.execute(select(Payment)).first() is None


def test_subscription_events_update_the_state(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, next_billing = active(harness, client)
    harness.paypal.set_subscription(subscription_id, "CANCELLED")  # cancelled from PayPal's website

    webhook(harness, "BILLING.SUBSCRIPTION.CANCELLED", {"id": subscription_id})

    user = client.get("/api/auth/me").get_json()["user"]
    assert user["subscription"]["status"] == "CANCELLED"
    assert datetime.fromisoformat(user["plan_expires_at"]) == next_billing


def test_suspended_subscription_keeps_the_plan_until_it_expires(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, next_billing = active(harness, client)
    harness.paypal.set_subscription(subscription_id, "SUSPENDED", next_billing)

    webhook(harness, "BILLING.SUBSCRIPTION.SUSPENDED", {"id": subscription_id})

    user = client.get("/api/auth/me").get_json()["user"]
    assert user["subscription"]["status"] == "SUSPENDED"
    assert datetime.fromisoformat(user["plan_expires_at"]) == next_billing + billing.GRACE


def test_events_about_other_apps_subscriptions_are_ignored(harness: Harness) -> None:
    harness.paypal.subscriptions["I-OTHER"] = {"id": "I-OTHER", "plan_id": "P-X", "custom_id": "", "status": "ACTIVE"}

    response = webhook(harness, "BILLING.SUBSCRIPTION.ACTIVATED", {"id": "I-OTHER"})

    assert response.get_json() == {"result": "processed"}


def test_a_paypal_outage_makes_paypal_retry_later(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    harness.paypal.fail = True

    response = webhook(harness, "BILLING.SUBSCRIPTION.UPDATED", {"id": subscription_id})

    assert response.status_code == 502
    with session_scope() as db:
        assert db.execute(select(WebhookEvent)).first() is None  # not marked: the retry will apply it


def test_events_without_an_id_are_refused(harness: Harness) -> None:
    body = json.dumps({"event_type": "PAYMENT.SALE.COMPLETED", "resource": {}})

    response = harness.client().post("/api/billing/webhook", data=body, content_type="application/json")

    assert response.status_code == 400


def test_an_order_approved_but_never_captured_by_the_browser(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"pack": "p500"}).get_json()["order_id"]
    # The buyer approved and closed the tab: only PayPal's event arrives.

    webhook(harness, "CHECKOUT.ORDER.APPROVED", {"id": order_id})

    assert harness.paypal.captured == [order_id]
    assert client.get("/api/auth/me").get_json()["user"]["page_credits"] == 500
    # The browser comes back late: nothing is charged or added twice.
    assert client.post(f"/api/billing/orders/{order_id}/capture").status_code == 200
    assert (
        webhook(
            harness,
            "PAYMENT.CAPTURE.COMPLETED",
            {
                "id": f"CAP-{order_id}",
                "supplementary_data": {"related_ids": {"order_id": order_id}},
            },
            event_id="WH-EVENT-2",
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").get_json()["user"]["page_credits"] == 500
    assert harness.paypal.captured == [order_id]
    with session_scope() as db:
        assert db.execute(select(Payment)).scalar_one().provider_capture_id == f"CAP-{order_id}"


def test_a_capture_completed_event_records_an_order_captured_elsewhere(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"pack": "p250"}).get_json()["order_id"]
    harness.paypal.capture_order(order_id)  # captured, but our server never heard about it

    webhook(harness, "PAYMENT.CAPTURE.COMPLETED", {"supplementary_data": {"related_ids": {"order_id": order_id}}})

    assert client.get("/api/auth/me").get_json()["user"]["page_credits"] == 250
    assert harness.paypal.captured == [order_id]  # not captured a second time


def test_a_refund_takes_the_pack_pages_back(harness: Harness) -> None:
    client = harness.signed_up()
    order_id = client.post("/api/billing/orders", json={"pack": "p1000"}).get_json()["order_id"]
    client.post(f"/api/billing/orders/{order_id}/capture")
    refund = {
        "id": "REFUND-1",
        "links": [{"rel": "up", "href": f"https://api.paypal.com/v2/payments/captures/CAP-{order_id}"}],
    }

    with session_scope() as db:
        db.execute(select(User)).scalar_one().page_credits = 600  # 400 pages already used

    webhook(harness, "PAYMENT.CAPTURE.REFUNDED", refund)

    assert client.get("/api/auth/me").get_json()["user"]["page_credits"] == 0
    with session_scope() as db:
        assert db.execute(select(Payment)).scalar_one().status == "REFUNDED"
    stats = harness.admin().get("/api/admin/stats").get_json()
    assert stats["revenue_usd"] == "0.00"


def test_a_reversed_subscription_payment(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    sale = {"id": "SALE-7", "billing_agreement_id": subscription_id, "amount": {"total": "4.99", "currency": "USD"}}
    webhook(harness, "PAYMENT.SALE.COMPLETED", sale)

    webhook(harness, "PAYMENT.SALE.REVERSED", {"id": "SALE-7"}, event_id="WH-EVENT-2")
    webhook(harness, "PAYMENT.SALE.REFUNDED", {"sale_id": "SALE-7"}, event_id="WH-EVENT-3")
    webhook(harness, "PAYMENT.CAPTURE.REVERSED", {"id": "UNKNOWN"}, event_id="WH-EVENT-4")
    webhook(harness, "PAYMENT.CAPTURE.REFUNDED", {"links": []}, event_id="WH-EVENT-5")

    with session_scope() as db:
        assert db.execute(select(Payment)).scalar_one().status == "REFUNDED"
    assert client.get("/api/auth/me").get_json()["user"]["plan"]["id"] == "free"


# --------------------------------------------------------------------------- reconciliation


def test_reconciliation_applies_a_renewal_whose_webhook_was_lost(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    now = utcnow() + timedelta(days=31)  # a month later, no webhook arrived
    renewed = (now + timedelta(days=30)).replace(microsecond=0)
    harness.paypal.set_subscription(subscription_id, "ACTIVE", renewed)

    with session_scope() as db:
        checked = billing.reconcile_subscriptions(db, harness.paypal, now)

    assert checked == 1
    assert account().plan_expires_at == renewed + billing.GRACE


def test_reconciliation_skips_failures_and_abandons_old_checkouts(harness: Harness) -> None:
    client = harness.signed_up()
    subscribe(client)  # never approved
    later = utcnow() + timedelta(days=4)

    with session_scope() as db:
        billing.reconcile_subscriptions(db, harness.paypal, later)
    with session_scope() as db:
        assert db.execute(select(Subscription)).scalar_one().status == "ABANDONED"

    other = harness.signed_up("bea@example.com")
    active(harness, other)
    harness.paypal.fail = True
    with session_scope() as db:
        assert billing.reconcile_subscriptions(db, harness.paypal, utcnow() + timedelta(days=40)) == 0


def test_admin_sees_subscriptions_and_payment_kinds(harness: Harness) -> None:
    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    sale = {"id": "SALE-3", "billing_agreement_id": subscription_id, "amount": {"total": "4.99", "currency": "USD"}}
    webhook(harness, "PAYMENT.SALE.COMPLETED", sale)
    admin = harness.admin()

    [row] = admin.get("/api/admin/users").get_json()["users"]
    assert row["subscription"]["status"] == "ACTIVE" and row["paid_total_usd"] == "4.99"
    assert admin.get("/api/admin/payments").get_json()["payments"][0]["kind"] == "subscription"
    assert admin.get("/api/admin/stats").get_json()["active_subscriptions"] == 1


def test_parse_time() -> None:
    assert billing.parse_time("2026-10-25T10:00:00Z") == datetime.fromisoformat("2026-10-25T10:00:00+00:00")
    assert billing.parse_time("not a date") is None
    assert billing.parse_time(None) is None


def test_deleting_the_account_cancels_the_subscription(harness: Harness) -> None:
    from tests.conftest import USER_PASSWORD

    client = harness.signed_up()
    subscription_id, _ = active(harness, client)
    harness.paypal.fail = True
    assert client.post("/api/auth/account/delete", json={"password": USER_PASSWORD}).status_code == 502
    assert account().status == "active"  # nothing deleted while PayPal could not cancel

    harness.paypal.fail = False
    assert client.post("/api/auth/account/delete", json={"password": USER_PASSWORD}).status_code == 200
    assert harness.paypal.cancelled == [subscription_id]
