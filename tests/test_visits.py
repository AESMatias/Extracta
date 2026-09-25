"""Unique visitors: counted per day without cookies, shown in /admin."""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.web.visits import VisitCounter
from tests.conftest import Harness
from tests.fakes import FakeRedis

FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
SAFARI = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


def visit(client: Any, user_agent: str = FIREFOX, ip: str = "203.0.113.7") -> Any:
    return client.post("/api/visit", headers={"User-Agent": user_agent}, environ_base={"REMOTE_ADDR": ip})


def visitors(harness: Harness) -> dict[str, Any]:
    summary: dict[str, Any] = harness.admin().get("/api/admin/stats").get_json()["visitors"]
    return summary


def test_the_same_visitor_counts_once_a_day_but_every_page_view_counts(harness: Harness) -> None:
    anyone = harness.client()

    for _ in range(3):
        assert visit(anyone).status_code == 204
    visit(anyone, user_agent=SAFARI)  # another browser
    visit(anyone, ip="198.51.100.4")  # another address

    summary = visitors(harness)
    assert (summary["today"], summary["views_today"]) == (3, 5)
    assert len(summary["days"]) == 30 and summary["days"][-1]["visitors"] == 3  # oldest first


def test_bots_and_requests_without_a_browser_are_not_visitors(harness: Harness) -> None:
    anyone = harness.client()

    for agent in ("Googlebot/2.1 (+http://www.google.com/bot.html)", "curl/8.5.0", "HeadlessChrome/120", ""):
        assert visit(anyone, user_agent=agent).status_code == 204

    assert visitors(harness)["views_today"] == 0


def test_one_address_cannot_inflate_the_count(harness: Harness) -> None:
    anyone = harness.client()

    for n in range(305):
        visit(anyone, user_agent=f"{FIREFOX} {n}")

    assert visitors(harness)["today"] == 300


def test_other_sites_cannot_count_visits(harness: Harness) -> None:
    response = harness.client().post("/api/visit", headers={"User-Agent": FIREFOX, "Origin": "https://evil.example"})

    assert response.status_code == 403


def test_a_visitor_who_returns_counts_once_over_the_week() -> None:
    redis = FakeRedis()
    counter = VisitCounter(redis, "k" * 32)

    counter.record("203.0.113.7", FIREFOX, NOW - timedelta(days=3))
    counter.record("203.0.113.7", FIREFOX, NOW)
    counter.record("198.51.100.4", FIREFOX, NOW - timedelta(days=10))

    summary = counter.summary(NOW)
    assert (summary["today"], summary["last_7_days"], summary["last_30_days"]) == (1, 1, 2)
    assert summary["views_30_days"] == 3
    # Only a keyed hash reaches Redis: the address never does.
    stored = {value for values in redis.sets.values() for value in values}
    assert all("203.0.113.7" not in value and len(value) == 64 for value in stored)
    assert all(ttl == 400 * 86400 for ttl in redis.ttls.values())


def test_visitor_stats_are_for_the_admin_only(harness: Harness) -> None:
    assert harness.signed_up().get("/api/admin/stats").status_code == 401
