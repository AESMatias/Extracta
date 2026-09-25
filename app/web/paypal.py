"""PayPal REST client (server side): Orders v2 for page packs, Subscriptions v1 for monthly
renewals, and webhook signature verification.

The browser shows PayPal's buttons; every amount, currency and plan is decided and verified here,
never trusted from the browser.
"""

import json
import time
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import httpx

from app.plans import PagePack, Plan

API_BASE = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}


class PayPalError(RuntimeError):
    pass


class PayPalClient:
    def __init__(
        self, *, client_id: str, client_secret: str, env: str, currency: str, http: httpx.Client | None = None
    ) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.env = env
        self.currency = currency
        self._base = API_BASE[env]
        self._http = http or httpx.Client(timeout=20)
        self._token: tuple[str, float] | None = None  # (access token, expiry as monotonic time)

    def _access_token(self) -> str:
        if self._token and self._token[1] > time.monotonic():
            return self._token[0]
        response = self._http.post(
            f"{self._base}/v1/oauth2/token",
            auth=(self.client_id, self._client_secret),
            data={"grant_type": "client_credentials"},
        )
        self._check(response)
        data = response.json()
        self._token = (data["access_token"], time.monotonic() + int(data.get("expires_in", 300)) - 60)
        return self._token[0]

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}", **kwargs.pop("headers", {})}
        try:
            response = self._http.request(method, f"{self._base}{path}", headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise PayPalError(f"cannot reach PayPal: {type(exc).__name__}") from exc
        self._check(response)
        if response.status_code == 204 or not response.content:  # e.g. cancelling a subscription
            return {}
        body: dict[str, Any] = response.json()
        return body

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise PayPalError(f"PayPal answered {response.status_code}")

    def create_order(self, *, pack: PagePack, custom_id: str) -> str:
        """A one-time payment for a page pack."""
        order = self._request(
            "POST",
            "/v2/checkout/orders",
            headers={"PayPal-Request-Id": str(uuid.uuid4())},  # idempotency key
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": pack.id,
                        "custom_id": custom_id,
                        "description": f"Extracta - {pack.pages:,} pages (prepaid, never expire)",
                        "amount": {"currency_code": self.currency, "value": str(pack.price_usd)},
                    }
                ],
            },
        )
        return str(order["id"])

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/checkout/orders/{order_id}")

    def capture_order(self, order_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v2/checkout/orders/{order_id}/capture",
            headers={"PayPal-Request-Id": f"capture-{order_id}", "Content-Type": "application/json"},
        )

    # ------------------------------------------------------------------ subscriptions

    def create_product(self) -> str:
        product = self._request(
            "POST",
            "/v1/catalogs/products",
            headers={"PayPal-Request-Id": f"extracta-product-{self.env}"},  # the same product on a retry
            json={
                "name": "Extracta",
                "description": "Turn PDFs into structured data",
                "type": "SERVICE",
                "category": "SOFTWARE",
            },
        )
        return str(product["id"])

    def create_billing_plan(self, *, product_id: str, plan: Plan) -> str:
        billing_plan = self._request(
            "POST",
            "/v1/billing/plans",
            headers={"PayPal-Request-Id": f"extracta-plan-{self.env}-{plan.id}-{plan.price_usd}"},
            json={
                "product_id": product_id,
                "name": f"Extracta {plan.name} (monthly)",
                "description": f"{plan.pages:,} pages every 30 days, renews every month",
                "status": "ACTIVE",
                "billing_cycles": [
                    {
                        "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                        "tenure_type": "REGULAR",
                        "sequence": 1,
                        "total_cycles": 0,  # renews until cancelled
                        "pricing_scheme": {
                            "fixed_price": {"value": str(plan.price_usd), "currency_code": self.currency}
                        },
                    }
                ],
                "payment_preferences": {
                    "auto_bill_outstanding": True,  # retry a failed payment on the next cycle
                    "payment_failure_threshold": 2,  # then PayPal suspends the subscription
                },
            },
        )
        return str(billing_plan["id"])

    def create_subscription(self, *, paypal_plan_id: str, custom_id: str, start_time: datetime | None) -> str:
        body: dict[str, Any] = {
            "plan_id": paypal_plan_id,
            "custom_id": custom_id,
            "application_context": {
                "brand_name": "Extracta",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
            },
        }
        if start_time is not None:  # first charge later, e.g. when a prepaid pass ends
            body["start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        subscription = self._request(
            "POST", "/v1/billing/subscriptions", headers={"PayPal-Request-Id": str(uuid.uuid4())}, json=body
        )
        return str(subscription["id"])

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/billing/subscriptions/{subscription_id}")

    def cancel_subscription(self, subscription_id: str, *, reason: str) -> None:
        self._request("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel", json={"reason": reason})

    # ------------------------------------------------------------------ webhooks

    def verify_webhook(self, *, headers: Mapping[str, str], raw_body: str, webhook_id: str) -> bool:
        """Ask PayPal whether this event really comes from PayPal for our webhook.

        The event is forwarded byte for byte as received: re-serializing it could change the
        bytes PayPal signed. It is embedded only after checking it is a single JSON object, so it
        cannot add or override fields of the verification request.
        """
        names = ("auth_algo", "cert_url", "transmission_id", "transmission_sig", "transmission_time")
        values = {name: headers.get(f"PAYPAL-{name.upper().replace('_', '-')}", "") for name in names}
        if not all(values.values()):
            return False
        try:
            event = json.loads(raw_body)
        except ValueError:
            return False
        if not isinstance(event, dict):
            return False
        fields = json.dumps({**values, "webhook_id": webhook_id})
        payload = fields[:-1] + ', "webhook_event": ' + raw_body + "}"
        result = self._request(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            content=payload.encode(),
            headers={"Content-Type": "application/json"},
        )
        return result.get("verification_status") == "SUCCESS"
