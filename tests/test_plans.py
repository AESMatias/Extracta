from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.plans import PAID_PLAN_IDS, PLANS, effective_plan, get_plan

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
GEMINI_COST_PER_DOC = Decimal("0.0006")  # measured in step 9


def test_there_is_a_free_plan_and_four_paid_plans() -> None:
    assert list(PLANS) == ["free", "starter", "pro", "business", "ultra"]
    assert PAID_PLAN_IDS == ["starter", "pro", "business", "ultra"]


def test_free_plan_allows_two_pdfs_a_day_and_no_database() -> None:
    free = PLANS["free"]

    assert free.price_usd == 0
    assert free.docs_per_24h == 2
    assert free.can_save_to_db is False


def test_plans_grow_in_price_and_volume() -> None:
    plans = list(PLANS.values())

    assert [p.price_usd for p in plans] == sorted(p.price_usd for p in plans)
    assert [p.docs_per_24h for p in plans] == sorted(p.docs_per_24h for p in plans)


def test_every_paid_plan_covers_its_worst_case_llm_cost() -> None:
    for plan_id in PAID_PLAN_IDS:
        plan = PLANS[plan_id]
        worst_case = plan.docs_per_24h * 30 * GEMINI_COST_PER_DOC
        assert plan.price_usd > worst_case, plan_id


def test_expired_pass_falls_back_to_free() -> None:
    assert effective_plan("pro", NOW - timedelta(seconds=1), NOW).id == "free"
    assert effective_plan("pro", NOW + timedelta(days=3), NOW).id == "pro"
    assert effective_plan("pro", None, NOW).id == "pro"  # assigned by the admin without expiry


def test_unknown_plan_ids_are_treated_as_free() -> None:
    assert get_plan("platinum").id == "free"


def test_plan_serialization_lists_explicit_privileges() -> None:
    data = PLANS["pro"].to_dict()

    assert data["price_usd"] == "4.99"
    assert data["duration_days"] == 30
    assert data["privileges"] == {
        "docs_per_24h": 100,
        "max_file_mb": 50,
        "max_files_per_upload": 25,
        "can_save_to_db": True,
        "export_formats": ["csv", "xlsx", "json"],
    }
