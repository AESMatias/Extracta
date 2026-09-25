"""PayPal Orders API v2 client (server side).

The browser shows PayPal's buttons; every amount, currency and plan is decided and verified here,
never trusted from the browser.
"""

import time
import uuid
from typing import Any

import httpx

from app.plans import PLAN_DURATION_DAYS, Plan

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
        body: dict[str, Any] = response.json()
        return body

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise PayPalError(f"PayPal answered {response.status_code}")

    def create_order(self, *, plan: Plan, custom_id: str) -> str:
        order = self._request(
            "POST",
            "/v2/checkout/orders",
            headers={"PayPal-Request-Id": str(uuid.uuid4())},  # idempotency key
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": plan.id,
                        "custom_id": custom_id,
                        "description": f"Extracta {plan.name} plan - {PLAN_DURATION_DAYS} days",
                        "amount": {"currency_code": self.currency, "value": str(plan.price_usd)},
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
