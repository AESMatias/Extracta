# Extracta — Intelligent Document Processing

![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-3.1-000000?logo=flask&logoColor=white)
![Next.js](https://img.shields.io/badge/next.js-16-000000?logo=nextdotjs&logoColor=white)
![Celery](https://img.shields.io/badge/celery-5.6-37814A?logo=celery&logoColor=white)
![Supabase](https://img.shields.io/badge/supabase-postgres%2017-3FCF8E?logo=supabase&logoColor=white)
![Gemini](https://img.shields.io/badge/LLM-Gemini%20Flash--Lite-4285F4?logo=googlegemini&logoColor=white)
![Nginx](https://img.shields.io/badge/nginx-1.30-009639?logo=nginx&logoColor=white)
![Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black)

Upload PDFs and get their data back as structured JSON, tables, charts and Excel/CSV/JSON files.
Each document is **classified** (invoice, receipt, contract, bank statement, payslip, resume,
report…), its text is extracted and an LLM (Gemini by default) turns it into validated data.

Extracta is a complete SaaS: accounts (email + password or Google) with email verification and
password recovery, a free plan and four cheap paid plans with daily quotas, PayPal monthly
subscriptions or one-time passes, and an admin panel to approve accounts and assign privileges. It is built to run on a **2 GB RAM server** behind automatic HTTPS.

- **Deploy it**: [docs/DEPLOY.md](docs/DEPLOY.md) — from an empty VPS to HTTPS, step by step.
- **Progress and decisions**: [roadmap](02-DOCS/wiki/ftd/idp-mvp.md),
  [accounts and billing](02-DOCS/wiki/ftd/accounts-billing-nextjs.md),
  [decision log](02-DOCS/wiki/sdd/decisions.md).

---

## Contents

- [Features](#features)
- [Plans](#plans)
- [Architecture](#architecture)
- [Run it locally](#run-it-locally)
- [Configuration (`.env`)](#configuration-env)
- [Administration](#administration)
- [HTTP API](#http-api)
- [Development: tests and quality](#development-tests-and-quality)
- [Ruff: what it is and how to use it](#ruff-what-it-is-and-how-to-use-it)
- [Project structure](#project-structure)
- [Security](#security)
- [Conventions](#conventions)

---

## Features

| Area | What you get |
|---|---|
| **Extraction** | 10 document types in any language: invoices, receipts, purchase orders, quotes, bank statements, contracts, payslips, resumes, reports and "other". Amounts as numbers, dates as `YYYY-MM-DD`, currencies as ISO 4217. |
| **Processing modes** | *Process only*: nothing is stored, results expire after 1 hour. *Save to history* (paid plans): results are kept in the account. The PDF file is deleted right after processing in both modes. |
| **Exports** | Excel (XLSX with typed numbers and dates), CSV (UTF-8 with BOM) and JSON, per document or for the whole batch. |
| **Dashboard** | Drag and drop, upload progress, live status per document, detail view, charts by type and by currency, saved history. |
| **Accounts** | Email + password or Google sign-in, email verification, forgot/reset/change password. Optional manual approval of new accounts. |
| **Plans** | Charged per page. Free (10 pages every 24 hours), pay-as-you-go page packs that never expire, and four monthly subscriptions (cancel anytime). |
| **Admin** | `/admin` with `ADMIN_PASSWORD`: approve/reject/suspend accounts, assign plans with or without expiry, custom daily limits, payments and stats. |

Document types and extracted fields:

| Type | Extracted data |
|---|---|
| `invoice`, `receipt`, `purchase_order`, `quote` | Issuer, customer, tax IDs, dates, subtotal, taxes, total, currency, line items |
| `bank_statement` | Bank, holder, **last 4 account digits only**, period, balances, credits and debits |
| `contract` | Parties and roles, term, value, auto-renewal, termination notice, governing law, key obligations |
| `payslip` | Employer, employee, period, gross pay, deductions, net pay |
| `resume` | Name, contact, title, experience, skills, languages, education |
| `report` | Title, author, date, period, key findings |
| `other` | Title and summary |

## Plans and pages

Usage is measured in **PDF pages**: every page of every processed document counts once, and a
document that fails gives its pages back. Defined in [`app/plans.py`](app/plans.py) (the frontend
catalog is generated from it and a test fails if they drift).

| Plan | Price | Pages | Pages per PDF | MB per file | Files per upload | Save to history |
|---|---|---|---|---|---|---|
| Free | $0 | 10 every 24 h | 10 | 10 | 2 | — |
| Starter | $1.99 / month | 300 every 30 days | 30 | 20 | 10 | ✓ |
| Pro | $4.99 / month | 1,000 every 30 days | 60 | 50 | 25 | ✓ |
| Business | $9.99 / month | 2,500 every 30 days | 100 | 50 | 50 | ✓ |
| Ultra | $19.99 / month | 6,000 every 30 days | 150 | 50 | 50 | ✓ |

**Pay as you go**: page packs of 100 ($0.99), 250 ($1.99), 500 ($3.49), 1,000 ($5.99), 2,500
($12.99) and 5,000 ($22.99) pages. Prepaid pages never expire, are spent after the plan's pages,
and unlock PDFs of up to 100 pages and saving to the history. Every plan and pack covers its
worst-case LLM cost (≈ USD 0.0006 per page with Gemini Flash-Lite), which is checked by a test.

---

## Architecture

```mermaid
flowchart LR
    B[Browser] -- "HTTPS" --> C[frontend<br/>Nginx: static Next.js site<br/>+ HTTPS]
    C -- "/api/*" --> W[web<br/>Flask API + gunicorn]
    W -- "streams PDFs" --> V[(volume<br/>/tmp_uploads)]
    W -- "enqueue" --> R[(Redis<br/>queue, results, sessions data)]
    R --> K[worker<br/>Celery, concurrency 1<br/>+ orphan sweep]
    V --> K
    K -- "text + schema" --> L[Gemini / OpenAI]
    K -- "save (paid plans)" --> S[(Supabase<br/>PostgreSQL)]
    W -- "accounts, quotas, payments" --> S
    W -- "orders, subscriptions" --> P[PayPal]
    P -- "webhooks" --> W
    W -- "emails" --> M[SMTP provider]
    W -- "sign-in" --> G[Google OAuth]
    CB[certbot<br/>production only] -- "Let's Encrypt certificates" --> C
```

| Piece | Technology | Role |
|---|---|---|
| Frontend | Next.js 16 (static export), React 19, Tailwind CSS 4, Recharts | The website and dashboard; no Node.js at runtime |
| Edge | Nginx 1.30 + certbot (Let's Encrypt) | Nginx serves the site, proxies `/api` and terminates HTTPS; certbot obtains and renews the certificates |
| API | Flask 3.1, gunicorn (2 × 4 threads) | Accounts, quotas, uploads, task status, exports, admin, billing |
| Queue | Celery 5.6 + Redis 8 | One document at a time, results with a TTL, periodic cleanup |
| Extraction | pdfplumber + Gemini (`google-genai`), optional OpenAI | Text, then structured data validated by Pydantic |
| Database | Supabase PostgreSQL + SQLAlchemy 2 + Alembic | Accounts, usage, payments, saved documents (Row Level Security on) |
| Payments / sign-in | PayPal Orders v2 + Subscriptions + webhooks, Google OAuth 2.0 (PKCE) | Optional; enabled by `.env` |
| Email | Any SMTP provider (logs locally) | Verification, password reset, security notices |

**Memory on a 2 GB server** (limits in `docker-compose.yml`): frontend 64 MB, web 384 MB,
worker 768 MB, redis 128 MB, plus certbot 128 MB in production: 1344 MB locally, 1472 MB in
production. Measured under load: ~4 / 210 / 240 / 14 MB.

---

## Run it locally

Requirements: Docker with Compose (macOS without Docker Desktop:
`brew install colima docker docker-compose && colima start --cpu 2 --memory 2 --disk 30`),
a Supabase project and a Gemini API key. No Python or Node.js needed on your machine.

```bash
git clone https://github.com/AESMatias/Extracta.git
cd Extracta
cp .env.sample .env          # fill GEMINI_API_KEY, DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD
docker compose up -d --build
./scripts/docker-cleanup.sh  # optional: free the disk space used by the build
```

Open <http://localhost:8080>. The API migrates the database on start. `/admin` uses
`ADMIN_PASSWORD`.

Useful commands:

```bash
docker compose ps                      # status and health
docker compose logs -f web worker      # follow the API and the worker
docker stats --no-stream               # real memory usage
docker compose down                    # stop (volumes are kept)
```

**Frontend with hot reload** (optional, needs Node.js 22): run the stack, publish the API port
temporarily or run Flask locally, then `cd frontend && npm install && API_ORIGIN=http://localhost:8000 npm run dev`.

---

## Configuration (`.env`)

Every variable is documented in [`.env.sample`](.env.sample); `.env` and any copy of it are
git-ignored. Settings are validated at startup ([`app/config.py`](app/config.py)): a missing or
invalid value stops the app with a clear message.

| Group | Variables |
|---|---|
| LLM | `LLM_PROVIDER` (`gemini`/`openai`), `LLM_MODEL`, `GEMINI_API_KEY`, `OPENAI_API_KEY` |
| Database | `DATABASE_URL` (Supabase **Session pooler**, pasted as shown) |
| Site | `PUBLIC_BASE_URL`, `SITE_DOMAIN`, `LETSENCRYPT_EMAIL`, `COMPOSE_PROFILES`, `HTTP_PORT`, `HTTPS_PORT` |
| Sessions | `SECRET_KEY` (≥ 32 chars), `SESSION_COOKIE_SECURE` (`true` with HTTPS) |
| Accounts | `REQUIRE_MANUAL_APPROVAL`, `REQUIRE_EMAIL_VERIFICATION`, `ADMIN_PASSWORD` (≥ 12 chars; empty disables /admin) |
| Email | `SMTP_HOST` (empty = emails go to the logs), `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SECURITY`, `MAIL_FROM` |
| Google sign-in | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (redirect URI: `PUBLIC_BASE_URL/api/auth/google/callback`) |
| PayPal | `PAYPAL_ENV` (`sandbox`/`live`), `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` |
| Queue | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `RESULT_TTL_SECONDS` |
| Uploads | `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `ORPHAN_MAX_AGE_HOURS` |

To switch the LLM to OpenAI: set `LLM_PROVIDER=openai`, `LLM_MODEL` and `OPENAI_API_KEY`, then
`docker compose build --build-arg POETRY_EXTRAS=openai web`.

---

## Administration

Open `/admin` and enter `ADMIN_PASSWORD` (5 attempts per 15 minutes; the admin session lasts
2 hours and is separate from user accounts). For every account you see its status, effective
plan, **explicit privileges** (PDFs per 24 h, MB per file, files per upload, save to history),
usage, sign-in methods and payments, and you can:

- **Approve / reject / suspend**: rejected and suspended accounts are signed out at once.
- **Assign a plan** (e.g. premium for free) with an expiry date or none.
- **Set a custom daily limit** that overrides the plan's.

With `REQUIRE_MANUAL_APPROVAL=true`, new accounts wait as *pending* (they can sign in but not
upload) until you approve them.

---

## HTTP API

All routes are under `/api` and use the session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in
production). State-changing requests from other origins are refused.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | Accounts (JSON) |
| `GET` | `/api/auth/me` | Current account with plan and usage (`user: null` when signed out) |
| `GET` | `/api/auth/google/login` → `/api/auth/google/callback` | Google sign-in |
| `POST` | `/api/auth/email/verify`, `/api/auth/email/resend` | Email verification |
| `POST` | `/api/auth/password/forgot`, `/api/auth/password/reset`, `/api/auth/password/change` | Passwords |
| `POST` | `/api/upload?save_to_db=true\|false` | Multipart `files`; plan and quota enforced |
| `POST` | `/api/tasks/status` | `{"task_ids": [...]}` → status and result of your tasks |
| `GET` | `/api/tasks/<id>` | One task (404 if it is not yours) |
| `GET`, `DELETE` | `/api/documents`, `/api/documents/<id>` | Saved history |
| `POST` | `/api/export/{csv\|xlsx\|json}/{individual\|unified}` | File downloads |
| `GET` | `/api/plans`, `/api/billing/config`, `/api/billing/payments` | Plans and your payments |
| `POST` | `/api/billing/orders`, `/api/billing/orders/<id>/capture` | One-time pass (PayPal) |
| `POST` | `/api/billing/subscriptions`, `/api/billing/subscriptions/<id>/activate`, `/api/billing/subscription/cancel` | Monthly subscription (PayPal) |
| `POST` | `/api/billing/webhook` | PayPal events (signature verified with PayPal) |
| `*` | `/api/admin/...` | Admin (session from `ADMIN_PASSWORD`) |
| `GET` | `/api/health` | Health check |

---

## Development: tests and quality

The backend is built test-first. Unit tests use an in-memory SQLite database and fakes for
Redis, Celery, Google and PayPal; integration tests hit the real Supabase and Gemini.

```bash
# Backend (inside the dev image: no local Python needed)
docker build -f docker/Dockerfile --target dev -t pdf-process-pipeline:dev .
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev ruff format app tests
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev ruff check app tests
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev mypy app tests
docker run --rm --env-file .env -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest -m integration

# Frontend
docker run --rm -v "$PWD/frontend":/app -w /app node:22-alpine sh -c "npm ci && npx tsc --noEmit && npx eslint . && npm run build"

# Database migrations (applied automatically when the web container starts)
docker compose run --rm --no-deps web python -m app.migrate
```

| Tool | Checks | Bar |
|---|---|---|
| pytest + pytest-cov | Behavior (250+ tests) | All green; ≥ 70% coverage on changed code (currently ~95%) |
| ruff | Style and common bugs | Zero findings |
| mypy | Types | Zero errors |
| tsc + eslint | Frontend types and React rules | Zero errors |
| Trivy | Known vulnerabilities with an available fix | Zero HIGH/CRITICAL in both images |

**CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of the above on every push
and pull request and scans both images every Monday. **Dependabot** proposes weekly updates for
Python, npm, Docker base images and GitHub Actions.

Dependencies are managed with **Poetry** (`pyproject.toml` + `poetry.lock`) and **npm**
(`frontend/package-lock.json`).

---

## Ruff: what it is and how to use it

[**Ruff**](https://docs.astral.sh/ruff/) is a Python linter and formatter written in Rust. It does
two different jobs:

| Command | What it does | Analogy |
|---|---|---|
| `ruff check` | **Linter**: finds bugs and bad practices (unused imports, undefined names, unsorted imports, outdated syntax, overlong lines…) and **reports** them | Spell checker |
| `ruff format` | **Formatter**: **rewrites** the code in one consistent style | An editor's auto-format |

Configuration (`pyproject.toml`): `line-length = 120` (comments included) and rule sets `E`
(PEP 8), `F` (real errors), `I` (import order), `B` (common bugs), `UP` (modern syntax) and `SIM`
(simplifications). Comments to the right of code are welcome as long as the line fits in 120
characters; `ruff format` adds the two spaces before `#` that PEP 8 asks for.

Recommended flow: after editing, `ruff format` (fixes things itself), then `ruff check` (fix the
rest by hand or with `ruff check --fix`).

---

## Project structure

```
├── app/                         Python backend
│   ├── __init__.py              create_app(): the Flask API
│   ├── config.py                Settings validated from .env
│   ├── plans.py                 Plans, prices and privileges
│   ├── accounts.py              Registration, sign-in, Google, passwords, quota
│   ├── billing.py               Passes, subscriptions, refunds, webhooks, reconciliation
│   ├── mail.py, emails.py       SMTP (or logs) and the email templates
│   ├── tokens.py                Signed, expiring links for verification and password reset
│   ├── models.py, db.py         Tables (users, usage, payments, subscriptions, documents...) and sessions
│   ├── migrations/, migrate.py  Alembic migrations (run on start)
│   ├── schemas.py               DocumentSchema: what the LLM must return
│   ├── storage.py               Streaming uploads, orphan sweep
│   ├── pdf_text.py              Text extraction (pdfplumber)
│   ├── llm/                     Gemini, OpenAI and the provider selector
│   ├── celery_app.py, tasks.py  Queue and the processing task
│   ├── export.py                CSV, XLSX and JSON exports
│   └── web/                     Routes: documents, auth, admin, billing, security helpers
├── frontend/                    Next.js site (static export) + nginx/ config + Dockerfile
│   └── src/app/                 /, /login, /register, /app, /pricing, /account, /admin
├── tests/                       pytest suite (unit + integration)
├── docker/Dockerfile            API/worker image: builder → dev → runtime
├── docker/certbot/             Image that gets and renews the HTTPS certificate (production)
├── docker-compose.yml           frontend + web + worker + redis with memory limits
├── docs/DEPLOY.md               Production deployment guide
├── scripts/docker-cleanup.sh    Free disk space after builds
└── 02-DOCS/wiki/                Constitution, decisions and roadmaps
```

---

## Security

- **Secrets** only in `.env` (git- and Docker-ignored); `SecretStr` keeps them out of logs.
- **Passwords**: PBKDF2-SHA256 with 600,000 iterations; unknown emails take as long as wrong
  passwords; login, registration, password reset and the admin password are rate limited.
  Changing a password signs out every other session.
- **Email links**: signed and expiring (verification 3 days, reset 1 hour and single-use); the
  token travels after `#`, so it never reaches a server log. "Forgot password" answers the same
  whether the account exists or not, and emails leave on a background thread so timing does not
  tell either. Linking Google to an account whose email was never verified removes its password
  (account pre-hijacking).
- **Sessions**: signed `HttpOnly`, `SameSite=Lax` cookie (`Secure` in production); cross-site
  state-changing requests are refused; rejected or suspended accounts are signed out at once.
- **Authorization**: plans and quotas are enforced on the server before the upload body is read;
  tasks, results and saved documents are only served to their owner (404 otherwise).
- **Payments**: the server sets the price, then verifies owner, plan, amount and currency before
  capturing, and owner and billing plan before activating a subscription; captures are
  idempotent. Webhooks are verified with PayPal using the raw body and applied exactly once.
- **Uploads**: streamed to disk in 64 KB chunks, checked by content (`%PDF-`), stored under
  server-generated names, deleted after processing; a periodic sweep removes orphans.
- **LLM output** is validated against a strict schema; document content never reaches error
  messages; bank accounts keep only their last 4 digits.
- **Exports**: CSV cells that look like formulas are escaped; XLSX writes text as text.
- **Browser**: Content-Security-Policy, `nosniff`, no framing, `Referrer-Policy`; React escapes
  all output and the app never injects HTML.
- **Database**: Row Level Security on every table, so Supabase's public REST API cannot read them.
- **Containers**: non-root API image without pip; Debian and Alpine patches applied on every
  build; Nginx hides its version, refuses TLS for unknown host names and sends HSTS; Trivy: 0 fixable HIGH/CRITICAL vulnerabilities in all three images (API, Nginx, certbot).

---

## Conventions

- Everything in the repository is in **English**: code, comments, docs and commit messages.
- Work happens on branches and reaches `main` through pull requests after CI passes.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org) with a descriptive
  subject that starts with an imperative verb, no emoji.
- Significant decisions are logged in [`02-DOCS/wiki/sdd/decisions.md`](02-DOCS/wiki/sdd/decisions.md).

The repository also carries an [rsc-harness](https://ericrisco.github.io/rsc-harness/)
configuration for AI assistants (Claude Code and Gemini CLI); regenerate its local files after
cloning with `npx @ericrisco/rsc@latest sync`.
