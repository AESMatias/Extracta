from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.plans import PAGE_PACKS, PAID_PLAN_IDS, PLANS, catalog, effective_plan, get_plan

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
GEMINI_COST_PER_PAGE = Decimal("0.0006")  # a 1-page document cost this in step 9: generous per page


def test_there_is_a_free_plan_and_four_paid_plans() -> None:
    assert list(PLANS) == ["free", "starter", "pro", "business", "ultra"]
    assert PAID_PLAN_IDS == ["starter", "pro", "business", "ultra"]


def test_free_plan_allows_ten_pages_a_day_and_no_database() -> None:
    free = PLANS["free"]

    assert free.price_usd == 0
    assert (free.pages, free.window_hours, free.max_pages_per_pdf) == (10, 24, 10)
    assert free.can_save_to_db is False


def test_plans_grow_in_price_and_volume() -> None:
    paid = [PLANS[plan_id] for plan_id in PAID_PLAN_IDS]

    assert [p.price_usd for p in paid] == sorted(p.price_usd for p in paid)
    assert [p.pages for p in paid] == sorted(p.pages for p in paid)
    assert [p.max_pages_per_pdf for p in paid] == sorted(p.max_pages_per_pdf for p in paid)
    assert all(p.window_hours == 30 * 24 for p in paid)


def test_every_paid_plan_and_pack_covers_its_worst_case_llm_cost() -> None:
    for plan_id in PAID_PLAN_IDS:
        plan = PLANS[plan_id]
        assert plan.price_usd > plan.pages * GEMINI_COST_PER_PAGE, plan_id
    for pack in PAGE_PACKS.values():
        assert pack.price_usd > pack.pages * GEMINI_COST_PER_PAGE, pack.id


def test_bigger_packs_are_cheaper_per_page() -> None:
    per_page = [pack.price_per_page for pack in PAGE_PACKS.values()]

    assert per_page == sorted(per_page, reverse=True)


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
        "pages": 1000,
        "window_hours": 720,
        "max_pages_per_pdf": 60,
        "max_file_mb": 50,
        "max_files_per_upload": 25,
        "can_save_to_db": True,
        "export_formats": ["csv", "xlsx", "json"],
    }


def test_frontend_plan_catalog_matches_the_backend() -> None:
    # The landing page is prerendered with frontend/src/lib/plans.json; checkout always uses the
    # server's prices, but the page must not advertise different ones. Regenerate the file with
    # `python -m app.plans > frontend/src/lib/plans.json`.
    import json
    from pathlib import Path

    saved = json.loads((Path(__file__).parents[1] / "frontend/src/lib/plans.json").read_text())

    assert saved == catalog()
