"""Plans, page packs and the privileges each one grants. Everything is measured in PDF pages.

- Free: a small allowance of pages every 24 hours.
- Subscriptions (Starter, Pro, Business, Ultra): pages every 30 days, renewed monthly through
  PayPal. When a subscription ends the user falls back to Free. The admin can also assign any
  plan by hand, with or without an expiry date.
- Page packs (pay as you go): prepaid pages that never expire. They are spent after the plan's
  allowance runs out and also unlock larger PDFs and saving to the database.

Charging per page is fairer than per document: a 1-page receipt and a 60-page report cost what
they really cost to process.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

PlanId = Literal["free", "starter", "pro", "business", "ultra"]
PLAN_DURATION_DAYS = 30
EXPORT_FORMATS = ["csv", "xlsx", "json"]


@dataclass(frozen=True)
class Plan:
    id: PlanId
    name: str
    price_usd: Decimal  # per month; 0 for Free
    pages: int  # pages allowed in every rolling window
    window_hours: int  # 24 for Free, 30 days for subscriptions
    max_pages_per_pdf: int
    max_file_mb: int
    max_files_per_upload: int
    can_save_to_db: bool  # persistent mode
    tagline: str
    highlight: bool = False  # shown as the recommended plan

    @property
    def window(self) -> timedelta:
        return timedelta(hours=self.window_hours)

    def privileges(self) -> dict[str, Any]:
        return {
            "pages": self.pages,
            "window_hours": self.window_hours,
            "max_pages_per_pdf": self.max_pages_per_pdf,
            "max_file_mb": self.max_file_mb,
            "max_files_per_upload": self.max_files_per_upload,
            "can_save_to_db": self.can_save_to_db,
            "export_formats": EXPORT_FORMATS,
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


MONTH_HOURS = PLAN_DURATION_DAYS * 24

# Ordered from lowest to highest. Prices cover the LLM cost even when every page is used.
PLANS: dict[str, Plan] = {
    plan.id: plan
    for plan in (
        Plan("free", "Free", Decimal("0.00"), 10, 24, 10, 10, 2, False, "Try it with a few pages every day."),
        Plan(
            "starter",
            "Starter",
            Decimal("1.99"),
            300,
            MONTH_HOURS,
            30,
            20,
            10,
            True,
            "For freelancers and small monthly batches.",
        ),
        Plan(
            "pro",
            "Pro",
            Decimal("4.99"),
            1000,
            MONTH_HOURS,
            60,
            50,
            25,
            True,
            "For teams processing documents every day.",
            True,
        ),
        Plan(
            "business",
            "Business",
            Decimal("9.99"),
            2500,
            MONTH_HOURS,
            100,
            50,
            50,
            True,
            "High volume for growing businesses.",
        ),
        Plan(
            "ultra",
            "Ultra",
            Decimal("19.99"),
            6000,
            MONTH_HOURS,
            150,
            50,
            50,
            True,
            "Maximum volume for heavy workloads.",
        ),
    )
}
PAID_PLAN_IDS = [plan_id for plan_id, plan in PLANS.items() if plan.price_usd > 0]


@dataclass(frozen=True)
class PagePack:
    id: str
    pages: int
    price_usd: Decimal

    @property
    def price_per_page(self) -> Decimal:
        return (self.price_usd / self.pages).quantize(Decimal("0.0001"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pages": self.pages,
            "price_usd": str(self.price_usd),
            "price_per_page": str(self.price_per_page),
        }


# Pay as you go: the bigger the pack, the cheaper each page. Prepaid pages never expire.
PAGE_PACKS: dict[str, PagePack] = {
    pack.id: pack
    for pack in (
        PagePack("p100", 100, Decimal("0.99")),
        PagePack("p250", 250, Decimal("1.99")),
        PagePack("p500", 500, Decimal("3.49")),
        PagePack("p1000", 1000, Decimal("5.99")),
        PagePack("p2500", 2500, Decimal("12.99")),
        PagePack("p5000", 5000, Decimal("22.99")),
    )
}

# What prepaid pages unlock on top of the plan (the more generous value of the two applies).
PREPAID_PRIVILEGES = {
    "max_pages_per_pdf": 100,
    "max_file_mb": 50,
    "max_files_per_upload": 20,
}  # + saving to the database


def get_plan(plan_id: str) -> Plan:
    return PLANS.get(plan_id, PLANS["free"])


def effective_plan(plan_id: str, expires_at: datetime | None, now: datetime) -> Plan:
    """The plan in force right now: an expired plan falls back to Free."""
    if plan_id != "free" and expires_at is not None and expires_at <= now:
        return PLANS["free"]
    return get_plan(plan_id)


def catalog() -> dict[str, Any]:
    return {
        "plans": [plan.to_dict() for plan in PLANS.values()],
        "packs": [pack.to_dict() for pack in PAGE_PACKS.values()],
        "prepaid_privileges": PREPAID_PRIVILEGES,
    }


if __name__ == "__main__":  # pragma: no cover
    # Regenerate the frontend catalog:  python -m app.plans > frontend/src/lib/plans.json
    import json

    print(json.dumps(catalog(), indent=2))
