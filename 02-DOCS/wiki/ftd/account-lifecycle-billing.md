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
| 1 | Email sending (SMTP, log fallback, background thread) | unit tests | ⏳ |
| 2 | Tokens | unit tests: expiry, tampering, single-use reset | ⏳ |
| 3 | Migration 0003 (email_verified_at, subscriptions, paypal_plans, webhook_events, payment columns) | applied to Supabase; RLS on new tables | ⏳ |
| 4 | Email verification + gates on upload and payments | route tests | ⏳ |
| 5 | Forgot / reset / change password, session invalidation | route tests | ⏳ |
| 6 | Subscriptions: create, activate, cancel, deferred start | tests with a fake PayPal | ⏳ |
| 7 | Webhooks: signature, idempotency, every handled event | tests with a fake PayPal | ⏳ |
| 8 | Reconciliation task | unit test | ⏳ |
| 9 | Admin: verified flag, subscriptions, refunded payments | route tests | ⏳ |
| 10 | Frontend: verify, forgot, reset pages; account security and subscription; pricing toggle; admin | tsc, eslint, build, browser check | ⏳ |
| 11 | End to end on the running stack | HTTP script: register → email in logs → verify → reset | ⏳ |
| 12 | Docs: `.env.sample`, DEPLOY (SMTP, webhooks), README | — | ⏳ |
