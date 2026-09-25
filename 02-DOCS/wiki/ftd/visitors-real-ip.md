---
title: Unique visitor counter and real visitor addresses behind the host's Nginx
status: done
updated: 2026-09-25
---

# Unique visitor counter and real visitor addresses

## Intent

The owner wants to know how many different people visit the site, from /admin. Production runs
behind the server's own Nginx (other apps share the machine), so Extracta saw every visitor with
the Docker gateway's address: rate limits were shared by everyone and a visitor count would be 1.

## Scope

- `REAL_IP_FROM` (frontend container): trust `X-Forwarded-For` only from those networks.
- `POST /api/visit` from every page (not /admin); `GET /api/admin/stats` returns `visitors`.
- Admin: visitors panel (today, 7 and 30 days, page views, 30-day bars); deleted accounts show no
  actions and have their own filter; the Accounts total excludes them.
- Privacy policy (en/es) discloses the count.

## Design

Each visitor is `HMAC(SECRET_KEY, ip|user agent)` added to a Redis HyperLogLog per UTC day (TTL
400 days) plus a page-view counter. A HyperLogLog keeps only a cardinality estimate, never the
members, so nobody can be listed or followed; no cookie is set. Multi-day totals are HyperLogLog
unions, so a returning visitor counts once. Bots (user agent) are skipped and each address counts
at most 300 views per hour.

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Counter, endpoint, admin stats | `tests/test_visits.py` (same visitor once, bots, cap, cross-site 403, 7-day union, only hashes stored, admin only) | ✅ |
| 2 | Real address behind the host's Nginx | Local stack with `REAL_IP_FROM`: Nginx log shows the forwarded addresses and 2 addresses count 2; without it, forged headers are ignored (2 forged addresses count 1) | ✅ |
| 3 | Admin UI, privacy text | tsc and eslint clean | ✅ |
| 4 | Docs: `.env.sample`, DEPLOY "Behind an existing Nginx" | — | ✅ |

## Next

Owner: on the server set `REAL_IP_FROM=172.16.0.0/12`, pull, rebuild web and frontend.
