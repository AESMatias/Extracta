---
type: feature
title: Email verification, password reset, auto-renewing subscriptions and PayPal webhooks
tags: [ftd, accounts, email, billing, paypal, webhooks]
branch: feat/project-skeleton
---

# Email verification, password reset, auto-renewing subscriptions and PayPal webhooks

## Intent

Close the gaps left out of the accounts feature: prove that every account owns its email,
let users recover a forgotten password, let paid plans renew by themselves every month, and let
PayPal tell the server about payments, renewals, cancellations and refunds even when the
buyer's browser is gone. OCR stays out.

## Scope

- In: outgoing email (any SMTP provider), email verification, forgot/reset/change password,
  session invalidation on password change, PayPal Subscriptions (monthly auto-renewal) next to
  the existing one-time 30-day passes, cancelling a subscription, a verified PayPal webhook
  endpoint, a periodic reconciliation with PayPal, admin and frontend support for all of it.
- Not now: OCR, changing the email address, upgrading or downgrading a subscription in place
  (cancel and subscribe again), prorated refunds.

## Design

**Email** (`app/mail.py`, `app/emails.py`): `SmtpMailer` works with any provider (Brevo,
Resend, Mailgun, Gmail with an app password...). Emails leave on a background thread, so a slow
SMTP server never slows a request and response times do not reveal whether an email exists.
Without SMTP settings, `LogMailer` writes each email, links included, to the `web` logs, which
is enough to test locally.

**Tokens** (`app/tokens.py`): signed and timed with `itsdangerous` (ships with Flask), no table.
Verification links last 3 days. Reset links last 1 hour and carry a fingerprint of the current
password hash, so a link stops working once it has been used or the password changed.

**Email verification**: new accounts get a link; Google accounts count as verified. Unverified
accounts can sign in and look around, but uploading and paying need a verified email
(`REQUIRE_EMAIL_VERIFICATION=true` by default). The admin can mark an email verified.
Pre-hijacking defence: if someone registered a victim's address with a password and the victim
later signs in with Google, the unverified password is removed when Google is linked.

**Passwords**: forgot-password always answers the same (no account enumeration) and is rate
limited per IP and per email. Resetting also verifies the email (the link proved it). Every
password change signs out all other sessions (the session keeps the password fingerprint) and
sends a "your password was changed" email.

**Subscriptions** (PayPal Subscriptions API): the PayPal product and one billing plan per
Extracta plan and price are created on first use and stored in `paypal_plans`, so changing a
price in `app/plans.py` just creates a new billing plan. The server creates each subscription
(with `custom_id = user:plan`) and verifies owner and plan before activating it. The plan runs
until the next billing date plus 3 days of grace; each renewal pushes it one month further.
Subscribing to the plan of an active one-time pass starts billing when the pass ends, so no
paid day is lost. Cancelling stops renewals and keeps the plan until the paid period ends.

**Webhooks** (`POST /api/billing/webhook`): verified with PayPal's verify-webhook-signature API
using the raw body exactly as received. Each event is processed once (`webhook_events`, unique
event id, recorded in the same transaction as its effects); a failure answers 500 so PayPal
retries. Handled: subscription activated/updated/cancelled/suspended/expired/payment failed,
renewal payments (`PAYMENT.SALE.COMPLETED`), order approved or captured (finishes a checkout
whose browser closed early), refunds and reversals (payment marked, plan access revoked).

**Reconciliation**: a Celery beat task every 6 hours asks PayPal about active subscriptions
whose billing date has passed, so a lost webhook never leaves a paying user on Free.

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Email sending (SMTP, log fallback, background thread) | `tests/test_mail.py`: STARTTLS/SSL/none, login, escaping, failures swallowed | ✅ |
| 2 | Tokens | `tests/test_tokens.py`: expiry, tampering, wrong purpose, single-use reset | ✅ |
| 3 | Migration 0003 (email_verified_at, subscriptions, paypal_plans, webhook_events, payment columns) | Applied to Supabase; the integration test now checks RLS on every model table and the head revision | ✅ |
| 4 | Email verification + gates on upload and payments | `tests/test_account_lifecycle.py` | ✅ |
| 5 | Forgot / reset / change password, session invalidation | `tests/test_account_lifecycle.py` | ✅ |
| 6 | Subscriptions: create, activate, cancel, deferred start, no pass on top | `tests/test_subscriptions.py`, `tests/test_paypal_client.py` | ✅ |
| 7 | Webhooks: signature, idempotency, every handled event | `tests/test_subscriptions.py`; raw-body forwarding and smuggling attempt in `tests/test_paypal_client.py` | ✅ |
| 8 | Reconciliation task | `tests/test_subscriptions.py`, `tests/test_tasks.py` | ✅ |
| 9 | Admin: verified flag, subscriptions, refunded payments | route tests | ✅ |
| 10 | Frontend: verify, forgot, reset pages; account security and subscription; pricing toggle; admin | tsc and eslint clean, static build of 11 routes; public pages checked in a browser at desktop and 375 px | ✅ |
| 11 | End to end on the running stack | HTTP script through Nginx with the real Supabase (below) | ✅ |
| 12 | Docs: `.env.sample`, DEPLOY (SMTP, webhooks), README | — | ✅ |
| 13 | Real PayPal sandbox subscription and webhook | Needs the owner's sandbox credentials and a public HTTPS URL | ⏳ |

## Evidence

- 332 unit tests pass (96% coverage); ruff and mypy clean. New modules: `billing.py` 92%,
  `mail.py`, `emails.py` and `tokens.py` 100%.
- Integration: migration 0003 applied to the real Supabase; RLS on every table.
- End to end through Nginx with the real Supabase and SMTP unset (emails in the web logs):
  registration sends the link; upload before verifying → 403 with `verify_email`; the link
  opened from a browser without a session verifies the account; upload → 202; a tampered link →
  400. Forgot password answers the same for known and unknown emails; the reset link signs in,
  signs out the two other sessions, works once, and only the new password works afterwards.
  Change password with a wrong current one → 401, right one → 200 and the session stays.
  Subscribing and the webhook answer 503 while PayPal and the webhook ID are not configured.
  No token appears in Nginx's access log.
- Design review: a pass bought on top of a live subscription would be overwritten by the next
  renewal; refused with 409 (fixed during review).

## Next

Owner: configure an SMTP provider and the PayPal sandbox (client ID, secret and a webhook to a
public HTTPS URL), then run one real sandbox subscription: subscribe, see the renewal date in
/account, cancel, and check the payments tab in /admin.
