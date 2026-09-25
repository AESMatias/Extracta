"""Unique visitors, counted without cookies and without storing who visited.

The site pings POST /api/visit on every page it shows. Each visitor is an HMAC of their IP address
and browser (keyed with SECRET_KEY) that is added to a Redis HyperLogLog, one per day. A
HyperLogLog keeps only an estimate of how many different values it has seen (about 0.8% error),
never the values themselves, so nobody can be listed, recognised or followed afterwards. Days are
kept for 400 days; the admin panel reads today, the last 7 and the last 30 days.
"""

import hashlib
import hmac
import re
from datetime import datetime, timedelta
from typing import Any

from flask import Blueprint, current_app, request

from app.db import utcnow
from app.web.security import client_ip

visits = Blueprint("visits", __name__, url_prefix="/api")

KEEP_DAYS = 400
# Crawlers, link previews and headless browsers are not visitors.
_BOTS = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|curl|wget|python", re.IGNORECASE)


class VisitCounter:
    def __init__(self, client: Any, secret: str) -> None:
        self._client = client
        self._secret = secret.encode()

    def record(self, ip: str, user_agent: str, now: datetime) -> None:
        visitor = hmac.new(self._secret, f"{ip}|{user_agent}".encode(), hashlib.sha256).hexdigest()
        day = now.date().isoformat()
        ttl = KEEP_DAYS * 86400
        pipe = self._client.pipeline()
        pipe.pfadd(f"visits:unique:{day}", visitor)
        pipe.expire(f"visits:unique:{day}", ttl)
        pipe.incr(f"visits:views:{day}")
        pipe.expire(f"visits:views:{day}", ttl)
        pipe.execute()

    def summary(self, now: datetime, days: int = 30) -> dict[str, Any]:
        """Per-day visitors and page views, plus unique visitors over 7 and 30 days (a visitor who
        came on several days counts once)."""
        dates = [(now - timedelta(days=offset)).date().isoformat() for offset in range(days)]  # newest first
        unique = [f"visits:unique:{day}" for day in dates]
        pipe = self._client.pipeline()
        for key in unique:
            pipe.pfcount(key)
        for day in dates:
            pipe.get(f"visits:views:{day}")
        pipe.pfcount(*unique[:7])
        pipe.pfcount(*unique)
        results = pipe.execute()
        visitors, views = results[:days], results[days : 2 * days]
        return {
            "today": int(visitors[0]),
            "last_7_days": int(results[-2]),
            "last_30_days": int(results[-1]),
            "views_today": int(views[0] or 0),
            "views_30_days": sum(int(v or 0) for v in views),
            "days": [
                {"day": day, "visitors": int(v), "views": int(p or 0)}
                for day, v, p in reversed(list(zip(dates, visitors, views, strict=True)))  # oldest first
            ],
        }


@visits.post("/visit")
def record_visit() -> tuple[str, int]:
    user_agent = request.headers.get("User-Agent", "")[:512]
    if not user_agent or _BOTS.search(user_agent):
        return "", 204
    ip = client_ip()
    limiter = current_app.extensions["rate_limiter"]
    if limiter.hit(f"visit:{ip}", limit=300, window_seconds=3600):  # past that, stop counting silently
        counter: VisitCounter = current_app.extensions["visit_counter"]
        counter.record(ip, user_agent, utcnow())
    return "", 204
