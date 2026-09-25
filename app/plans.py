"""Subscription plans and the privileges each one grants.

Paid plans are 30-day passes bought through PayPal. When a pass expires the user falls back to
Free. The admin can also assign any plan by hand, with or without an expiry date.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

PlanId = Literal["free", "starter", "pro", "business", "ultra"]
PLAN_DURATION_DAYS = 30


@dataclass(frozen=True)
class Plan:
    id: PlanId
    name: str
    price_usd: Decimal  # per 30 days; 0 for Free
    docs_per_24h: int  # rolling window
    max_file_mb: int
    max_files_per_upload: int
    can_save_to_db: bool  # persistent mode
    tagline: str
    highlight: bool = False  # shown as the recommended plan

    def privileges(self) -> dict[str, Any]:
        return {
            "docs_per_24h": self.docs_per_24h,
            "max_file_mb": self.max_file_mb,
            "max_files_per_upload": self.max_files_per_upload,
            "can_save_to_db": self.can_save_to_db,
            "export_formats": ["csv", "xlsx", "json"],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price_usd": str(self.price_usd),
            "duration_days": 0 if self.id == "free" else PLAN_DURATION_DAYS,
            "tagline": self.tagline,
            "highlight": self.highlight,
            "privileges": self.privileges(),
        }


# Ordered from lowest to highest. Prices cover the LLM cost even at 100% daily usage.
PLANS: dict[str, Plan] = {
    plan.id: plan
    for plan in (
        Plan("free", "Free", Decimal("0.00"), 2, 10, 2, False, "Try it with a couple of documents a day."),
        Plan("starter", "Starter", Decimal("1.99"), 25, 20, 10, True, "For freelancers and small monthly batches."),
        Plan("pro", "Pro", Decimal("4.99"), 100, 50, 25, True, "For teams processing documents every day.", True),
        Plan("business", "Business", Decimal("9.99"), 250, 50, 50, True, "High volume for growing businesses."),
        Plan("ultra", "Ultra", Decimal("19.99"), 600, 50, 50, True, "Maximum volume for heavy workloads."),
    )
}
PAID_PLAN_IDS = [plan_id for plan_id, plan in PLANS.items() if plan.price_usd > 0]


def get_plan(plan_id: str) -> Plan:
    return PLANS.get(plan_id, PLANS["free"])


def effective_plan(plan_id: str, expires_at: datetime | None, now: datetime) -> Plan:
    """The plan in force right now: an expired pass falls back to Free."""
    if plan_id != "free" and expires_at is not None and expires_at <= now:
        return PLANS["free"]
    return get_plan(plan_id)


if __name__ == "__main__":  # pragma: no cover
    # Regenerate the frontend catalog:  python -m app.plans > frontend/src/lib/plans.json
    import json

    print(json.dumps([plan.to_dict() for plan in PLANS.values()], indent=2))
