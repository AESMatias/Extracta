"""The real PayPal client against a simulated PayPal (httpx.MockTransport): no network."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.plans import PLANS
from app.web.paypal import PayPalClient, PayPalError

WEBHOOK_HEADERS = {
    "PAYPAL-AUTH-ALGO": "SHA256withRSA",
    "PAYPAL-CERT-URL": "https://api.paypal.com/v1/notifications/certs/CERT-1",
    "PAYPAL-TRANSMISSION-ID": "tx-1",
    "PAYPAL-TRANSMISSION-SIG": "sig",
    "PAYPAL-TRANSMISSION-TIME": "2026-09-25T10:00:00Z",
}


class FakeApi:
    """Records requests and answers like PayPal's REST API."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.verification_status = "SUCCESS"
        self.fail_path: str | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == self.fail_path:
            return httpx.Response(500, json={})
        if path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        if path == "/v1/catalogs/products":
            return httpx.Response(201, json={"id": "PROD-1"})
        if path == "/v1/billing/plans":
            return httpx.Response(201, json={"id": "P-1"})
        if path == "/v1/billing/subscriptions":
            return httpx.Response(201, json={"id": "I-1", "status": "APPROVAL_PENDING"})
        if path.endswith("/cancel"):
            return httpx.Response(204)
        if path.startswith("/v1/billing/subscriptions/"):
            return httpx.Response(200, json={"id": path.rsplit("/", 1)[-1], "status": "ACTIVE"})
        if path == "/v1/notifications/verify-webhook-signature":
            return httpx.Response(200, json={"verification_status": self.verification_status})
        return httpx.Response(404, json={})

    def last(self, path: str) -> httpx.Request:
        return [r for r in self.requests if r.url.path == path][-1]


@pytest.fixture
def api() -> FakeApi:
    return FakeApi()


@pytest.fixture
def client(api: FakeApi) -> PayPalClient:
    return PayPalClient(
        client_id="id",
        client_secret="secret",
        env="sandbox",
        currency="USD",
        http=httpx.Client(transport=httpx.MockTransport(api)),
    )


def body(request: httpx.Request) -> Any:
    return json.loads(request.content)


def test_billing_plan_is_monthly_at_the_plan_price(client: PayPalClient, api: FakeApi) -> None:
    assert client.create_product() == "PROD-1"
    assert client.create_billing_plan(product_id="PROD-1", plan=PLANS["pro"]) == "P-1"

    plan = body(api.last("/v1/billing/plans"))
    [cycle] = plan["billing_cycles"]
    assert cycle["frequency"] == {"interval_unit": "MONTH", "interval_count": 1}
    assert cycle["total_cycles"] == 0
    assert cycle["pricing_scheme"]["fixed_price"] == {"value": "4.99", "currency_code": "USD"}
    assert api.last("/v1/billing/plans").headers["PayPal-Request-Id"] == "extracta-plan-sandbox-pro-4.99"
    assert api.last("/v1/catalogs/products").headers["Authorization"] == "Bearer token-1"


def test_create_subscription_with_and_without_a_start_date(client: PayPalClient, api: FakeApi) -> None:
    assert client.create_subscription(paypal_plan_id="P-1", custom_id="u:pro", start_time=None) == "I-1"
    assert "start_time" not in body(api.last("/v1/billing/subscriptions"))

    start = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)
    client.create_subscription(paypal_plan_id="P-1", custom_id="u:pro", start_time=start)
    sent = body(api.last("/v1/billing/subscriptions"))
    assert sent["start_time"] == "2026-10-25T10:00:00Z"
    assert sent["custom_id"] == "u:pro" and sent["application_context"]["shipping_preference"] == "NO_SHIPPING"


def test_get_and_cancel_subscription(client: PayPalClient, api: FakeApi) -> None:
    assert client.get_subscription("I-9")["id"] == "I-9"
    client.cancel_subscription("I-9", reason="bye")  # PayPal answers 204 with no body

    assert body(api.last("/v1/billing/subscriptions/I-9/cancel")) == {"reason": "bye"}


def test_verify_webhook_forwards_the_raw_event(client: PayPalClient, api: FakeApi) -> None:
    raw = '{"id": "WH-1",   "event_type": "X", "resource": {"amount": 4.990}}'

    assert client.verify_webhook(headers=WEBHOOK_HEADERS, raw_body=raw, webhook_id="WH-ID") is True

    sent = api.last("/v1/notifications/verify-webhook-signature").content.decode()
    assert sent.endswith(', "webhook_event": ' + raw + "}")  # byte for byte, 4.990 included
    fields = json.loads(sent)
    assert fields["webhook_id"] == "WH-ID"
    assert fields["transmission_id"] == "tx-1" and fields["auth_algo"] == "SHA256withRSA"


def test_verify_webhook_failures(client: PayPalClient, api: FakeApi) -> None:
    raw = '{"id": "WH-1"}'
    api.verification_status = "FAILURE"
    assert client.verify_webhook(headers=WEBHOOK_HEADERS, raw_body=raw, webhook_id="W") is False

    api.verification_status = "SUCCESS"
    missing = {k: v for k, v in WEBHOOK_HEADERS.items() if k != "PAYPAL-TRANSMISSION-SIG"}
    assert client.verify_webhook(headers=missing, raw_body=raw, webhook_id="W") is False
    assert client.verify_webhook(headers=WEBHOOK_HEADERS, raw_body="not json", webhook_id="W") is False
    assert client.verify_webhook(headers=WEBHOOK_HEADERS, raw_body="[1, 2]", webhook_id="W") is False
    # An attacker cannot smuggle a second webhook_id after the event: trailing data is not JSON.
    smuggled = '{"id": "x"}, "webhook_id": "attacker"'
    assert client.verify_webhook(headers=WEBHOOK_HEADERS, raw_body=smuggled, webhook_id="W") is False


def test_paypal_errors_raise(client: PayPalClient, api: FakeApi) -> None:
    api.fail_path = "/v1/billing/subscriptions/I-1"

    with pytest.raises(PayPalError):
        client.get_subscription("I-1")


def test_access_token_is_reused(client: PayPalClient, api: FakeApi) -> None:
    client.get_subscription("I-1")
    client.get_subscription("I-2")

    assert sum(r.url.path == "/v1/oauth2/token" for r in api.requests) == 1
