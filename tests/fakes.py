"""In-memory stand-ins for Redis, the Celery queue, PayPal, Google and email, used by the API tests."""

import itertools
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from app.plans import Plan
from app.web.google import GoogleAuthError, GoogleProfile
from app.web.paypal import PayPalError
from app.web.queue import TaskStatus


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self) -> "FakePipeline":
        return FakePipeline(self)

    def incr(self, key: str) -> int:
        self.values[key] = int(self.values.get(key, 0)) + 1
        return int(self.values[key])

    def expire(self, key: str, seconds: int, nx: bool = False) -> bool:
        if nx and key in self.ttls:
            return False
        self.ttls[key] = seconds
        return True

    def set(self, key: str, value: Any, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self.values:
            return None
        self.values[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            removed += int(self.values.pop(key, None) is not None or self.sets.pop(key, None) is not None)
            self.ttls.pop(key, None)
        return removed

    def sadd(self, key: str, *values: str) -> int:
        self.sets.setdefault(key, set()).update(values)
        return len(values)

    def sismember(self, key: str, value: str) -> bool:
        return value in self.sets.get(key, set())


class FakePipeline:
    def __init__(self, redis: FakeRedis) -> None:
        self._redis = redis
        self._calls: list[Callable[[], Any]] = []

    def __getattr__(self, name: str) -> Callable[..., "FakePipeline"]:
        method = getattr(self._redis, name)

        def queue(*args: Any, **kwargs: Any) -> "FakePipeline":
            self._calls.append(lambda: method(*args, **kwargs))
            return self

        return queue

    def execute(self) -> list[Any]:
        results = [call() for call in self._calls]
        self._calls = []
        return results


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []
        self.statuses: dict[str, TaskStatus] = {}

    def enqueue(self, file_path: Path, filename: str, save_to_db: bool, user_id: str | None) -> str:
        task_id = str(uuid.uuid4())
        self.enqueued.append(
            {"task_id": task_id, "path": file_path, "filename": filename, "save_to_db": save_to_db, "user_id": user_id}
        )
        self.statuses[task_id] = TaskStatus(status="pending")
        return task_id

    def status(self, task_id: str) -> TaskStatus:
        return self.statuses.get(task_id, TaskStatus(status="pending"))


class FakePayPal:
    client_id = "paypal-client-id"
    currency = "USD"
    env = "sandbox"

    def __init__(self) -> None:
        self.orders: dict[str, dict[str, Any]] = {}
        self.captured: list[str] = []
        self.capture_status = "COMPLETED"
        self.fail = False
        self._ids = itertools.count(1)
        self.products: list[str] = []
        self.billing_plans: dict[str, Plan] = {}
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.cancelled: list[str] = []
        self.webhook_valid = True
        self.verified_bodies: list[str] = []

    # one-time orders
    def create_order(self, *, plan: Plan, custom_id: str) -> str:
        if self.fail:
            raise PayPalError("down")
        order_id = f"ORDER{next(self._ids)}"
        self.orders[order_id] = {
            "id": order_id,
            "status": "APPROVED",  # as if the buyer already approved it in PayPal's window
            "purchase_units": [
                {"custom_id": custom_id, "amount": {"currency_code": "USD", "value": str(plan.price_usd)}}
            ],
        }
        return order_id

    def get_order(self, order_id: str) -> dict[str, Any]:
        if order_id not in self.orders:
            raise PayPalError("404")
        return self.orders[order_id]

    def capture_order(self, order_id: str) -> dict[str, Any]:
        if self.fail:
            raise PayPalError("down")
        self.captured.append(order_id)
        order = self.orders[order_id]
        order["status"] = self.capture_status
        order["purchase_units"][0]["payments"] = {
            "captures": [{"id": f"CAP-{order_id}", "status": self.capture_status}]
        }
        return order

    # subscriptions
    def create_product(self) -> str:
        self.products.append(f"PROD-{len(self.products) + 1}")
        return self.products[-1]

    def create_billing_plan(self, *, product_id: str, plan: Plan) -> str:
        plan_id = f"P-{plan.id.upper()}-{next(self._ids)}"
        self.billing_plans[plan_id] = plan
        return plan_id

    def create_subscription(self, *, paypal_plan_id: str, custom_id: str, start_time: datetime | None) -> str:
        if self.fail:
            raise PayPalError("down")
        subscription_id = f"I-SUB{next(self._ids)}"
        self.subscriptions[subscription_id] = {
            "id": subscription_id,
            "plan_id": paypal_plan_id,
            "custom_id": custom_id,
            "status": "APPROVAL_PENDING",
            "start_time": start_time,
            "billing_info": {},
        }
        return subscription_id

    def set_subscription(self, subscription_id: str, status: str, next_billing: datetime | None = None) -> None:
        """What PayPal would report after the buyer approves, a renewal, a suspension..."""
        data = self.subscriptions[subscription_id]
        data["status"] = status
        data["billing_info"] = (
            {"next_billing_time": next_billing.strftime("%Y-%m-%dT%H:%M:%SZ")} if next_billing else {}
        )

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        if self.fail:
            raise PayPalError("down")
        if subscription_id not in self.subscriptions:
            raise PayPalError("404")
        return self.subscriptions[subscription_id]

    def cancel_subscription(self, subscription_id: str, *, reason: str) -> None:
        if self.fail:
            raise PayPalError("down")
        self.cancelled.append(subscription_id)
        self.set_subscription(subscription_id, "CANCELLED")

    # webhooks
    def verify_webhook(self, *, headers: Mapping[str, str], raw_body: str, webhook_id: str) -> bool:
        self.verified_bodies.append(raw_body)
        return self.webhook_valid


class FakeGoogle:
    def __init__(self) -> None:
        self.profile = GoogleProfile(sub="google-sub-1", email="gina@example.com", email_verified=True, name="Gina")
        self.fail = False
        self.last_state: str | None = None

    def authorization_url(self, *, state: str, code_verifier: str) -> str:
        self.last_state = state
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    def fetch_profile(self, *, code: str, code_verifier: str) -> GoogleProfile:
        if self.fail:
            raise GoogleAuthError("bad code")
        return self.profile


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)

    def last_to(self, address: str) -> EmailMessage:
        return [m for m in self.sent if m["To"] == address][-1]

    def link_token(self, address: str) -> str:
        """The token of the last link sent to this address (links look like .../page#token=...)."""
        body = self.last_to(address).get_body(("plain",))
        assert body is not None
        match = re.search(r"#token=(\S+)", body.get_content())
        assert match, "no link in the email"
        return match.group(1)
