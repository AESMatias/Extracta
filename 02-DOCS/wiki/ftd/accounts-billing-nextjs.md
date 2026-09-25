---
type: feature
title: Accounts, plans, admin, PayPal and the Next.js frontend
tags: [ftd, accounts, billing, frontend, deploy]
branch: feat/project-skeleton
---

# Accounts, plans, admin, PayPal and the Next.js frontend

## Intent

Turn the IDP MVP into a service that can be published: users register (email + password or
Google), use a free plan limited to 2 PDFs every 24 hours or buy cheap 30-day passes through
PayPal, and the owner manages accounts and privileges from `/admin`. Replace the plain HTML page
with a polished, mobile-first Next.js frontend and make the stack deployable to a 2 GB server
with automatic HTTPS. Close the pending follow-ups: orphaned uploads, base-image patching and
database migrations.

## Scope

- In: accounts, sessions, Google sign-in, plans and quotas, admin API and page, PayPal
  checkout, Alembic, orphan sweep, Next.js site (landing, auth, dashboard, pricing, account,
  admin), Caddy with HTTPS and CSP, deployment guide, CI and Dependabot.
- Not now: email verification and password reset by email (needs an email provider),
  subscriptions with automatic renewal, PayPal webhooks, OCR, translations of the UI.

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Plans and privileges | `tests/test_plans.py`: catalog, prices cover LLM cost, frontend copy matches | ✅ |
| 2 | Accounts and Google | `tests/test_accounts.py`, `tests/test_auth_routes.py` | ✅ |
| 3 | Quotas and ownership on every document route | `tests/test_web.py` | ✅ |
| 4 | Admin API | `tests/test_admin_routes.py` | ✅ |
| 5 | PayPal checkout | `tests/test_billing.py` (fake PayPal: tampering, idempotency, extension) | ✅ |
| 6 | Alembic | Migrations applied to the real Supabase; integration test checks RLS on every table | ✅ |
| 7 | Orphan sweep | `tests/test_storage.py`, `tests/test_tasks.py` | ✅ |
| 8 | Next.js frontend | `tsc`, `eslint`, static build of 8 routes; reviewed in a browser on desktop and mobile | ✅ |
| 9 | Caddy, compose, deploy guide | Stack up through Caddy; HTTP end-to-end run; `docs/DEPLOY.md` | ✅ |
| 10 | CI, Dependabot, image patching | `.github/`; Trivy: 0 fixable HIGH/CRITICAL in both images | ✅ |
| 11 | Real PDFs, PayPal sandbox, Google credentials | Needs the owner's documents and credentials | ⏳ |

## Evidence

- Backend: 250 unit tests pass (95% coverage), ruff and mypy clean; unit tests run on an
  in-memory SQLite database with fakes for Redis, Celery, Google and PayPal.
- Migrations on the real Supabase: the step-6 `documents` table adopted as 0001; 0002 created
  `users`, `usage_events`, `payments` and `documents.user_id`; RLS on every table including
  `alembic_version`.
- End to end through Caddy with the real Gemini and Supabase: registration (Free), save-to-DB
  refused (403), 3 files refused (400), 2 PDFs accepted, third refused with the next free slot
  (429), both completed in 7.6 s, another account gets `not_found` for them, admin login
  (wrong 401, right 200), upgrade to Pro, saved document listed, suspension ends the session,
  cross-site POST refused (403). Test accounts deleted afterwards.
- Memory under that run: frontend 12 MiB, web 210 MiB, worker 237 MiB, redis 14 MiB.
- Browser review: landing, pricing, sign-in, registration, admin gate and 404 on desktop and
  375 px mobile; no horizontal overflow. Fixed during review: cramped 5-column plans at 1024 px,
  logo gradient lost when two logos shared an SVG id, 401 noise in the console for visitors.
- Images: the API image had 0 fixable HIGH/CRITICAL; the official Caddy binary had 17 (old Go
  and modules), fixed by compiling Caddy 2.11.4 with Go 1.26.8 and patched modules (grpc pinned
  to 1.83.2) → 0.
- Incident: the Mac ran out of disk (Colima's disk image grew with build caches) and Docker's
  store hit I/O errors. Freed by deleting regenerable caches, restarting Colima and trimming the
  VM disk; `scripts/docker-cleanup.sh` now does this in one step.

## Next

Owner: test the dashboard with real PDFs, create PayPal sandbox and Google OAuth credentials,
then deploy with `docs/DEPLOY.md`.
