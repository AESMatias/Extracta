---
type: feature
title: IDP MVP — batch PDF upload with background LLM extraction
tags: [ftd, idp]
branch: feat/project-skeleton
---

# IDP MVP — batch PDF upload with background LLM extraction

## Intent

A web UI where a user uploads many PDFs at once; a single Celery worker processes them one by
one (2 GB RAM server), extracts text with `pdfplumber`, turns it into a validated
`DocumentSchema` with an LLM (Gemini by default, switchable via `.env`) and deletes the PDF.

On upload the user picks a mode: **persistent** (save to Supabase) or **ephemeral** (never touch
the database). In both modes the task returns the extracted data, Celery keeps it in the Redis
result backend for a limited time, and the browser renders it as tables and charts. Two buttons
export CSV: one document, or the whole batch merged. The owner is learning Flask, so work
advances one reviewed step at a time.

## Scope

- In: Flask + Jinja2 UI, streaming uploads, Celery + Redis queue (+ Redis result backend with
  TTL), persistent/ephemeral toggle, Supabase storage (persistent mode only), provider-agnostic
  LLM layer, individual and unified CSV export, live charts (Chart.js), Docker Compose with
  memory limits, tests.
- Not now: authentication, multi-tenant users, OCR for scanned PDFs, VPS deployment (a later
  feature).

## Checklist

Each step = one file (or a tiny group) + its tests, reviewed and committed before the next.

| # | Step | Files | Proof it is done | Status |
|---|------|-------|------------------|--------|
| 0 | Harness + local tooling | `.rsc.json`, Colima/Docker | `RSC_ONBOARDING_READY`; `docker compose version` | ✅ |
| 1 | Base configuration | `pyproject.toml`, `docker-compose.yml`, `.env.sample` | `docker compose config` OK | ✅ Add Poetry config, Docker Compose stack and env sample |
| 2 | Docker image | `docker/Dockerfile`, `.dockerignore`, `poetry.lock` | Dependency stage builds and imports; Trivy scan reviewed | ✅ Add multi-stage Dockerfile, .dockerignore and poetry.lock |
| 3 | Settings | `app/config.py` + test | Missing/invalid `.env` values fail at startup with a clear error | ✅ Add validated settings loaded from .env |
| 4 | Flask app factory + health check | `app/__init__.py` + test | Full image builds; `docker compose up web redis` → `GET /health` 200 | ✅ Add Flask app factory with a health check endpoint |
| 5 | Extraction schema | `app/schemas.py` + test | `DocumentSchema` validates/rejects sample payloads | ✅ Add multi-type extraction schema for the LLM |
| 6 | Database | `app/db.py`, `app/models.py` + test | `documents` table (persistent mode) created in Supabase with RLS on; insert/read round-trip | ✅ Add Supabase database layer and documents table |
| 7 | Streaming upload storage | `app/storage.py` + test | Large file written in chunks; RAM stays flat | ✅ Add streaming PDF upload storage with size and header checks |
| 8 | PDF text extraction | `app/pdf_text.py` + test | Text extracted from a sample PDF | ✅ Add page-by-page PDF text extraction with an LLM character cap |
| 9 | LLM layer | `app/llm/{base,gemini,openai,factory}.py` + tests | Factory picks provider from `.env`; Gemini returns a `DocumentSchema` | ✅ Add provider-agnostic LLM extraction with Gemini and optional OpenAI |
| 10 | Celery task | `app/tasks.py` + test | `save_to_db` true → row in Supabase; false → no DB call; both return the data (Redis backend, TTL); PDF deleted in every outcome | ✅ Add Celery document processing task with persistent and ephemeral modes |
| 11 | Export (CSV, XLSX, JSON) | `app/export.py` + test | Individual (one doc, line items as rows) and unified (one row per doc) in CSV, XLSX and JSON; formula injection blocked | ✅ Add individual and unified CSV export with formula injection protection |
| 12 | Web routes | `app/web/routes.py` + tests | `POST /upload` (+ `save_to_db`) → task ids; `GET /tasks/<id>` → status + result; `POST /export/csv/individual` and `/unified` stream CSV | ✅ Add the HTTP API with per-browser task ownership |
| 13 | UI | `app/web/templates/`, `app/web/static/` | Dropzone + mode toggle + polling + results table + Chart.js charts + both CSV buttons | ⏳ next |
| 14 | Verify | — | ruff, mypy, pytest ≥ 70% coverage all green; Trivy re-scan | ⬜ |
| 15 | End-to-end + merge | — | Batch of real PDFs in both modes under the 2 GB limits; merged to `main` | ⬜ |

## Evidence

- Step 0: `RSC_ONBOARDING_READY 63371e3d…`; Docker 29.8.1 / Compose 5.5.1 on Colima (2 CPU, 2 GB).
- Step 1: `docker compose config` → OK; limits web 384M, worker 768M, redis 128M (sum 1280M).
- Step 2: builder stage imports Flask 3.1.3, Celery 5.6.3, Pydantic 2.13.5, google-genai;
  `POETRY_EXTRAS=openai` adds openai 3.19.2. Trivy on `poetry.lock`: 0 vulnerabilities.
  Trivy on `python:3.12-slim` (Debian 13.7): HIGH findings only in OS packages with no fix
  released upstream — see decision 2026-09-24 in `02-DOCS/wiki/sdd/decisions.md`.

- Step 3: TDD red (`ModuleNotFoundError: app`) → green: 11 tests pass, `app/config.py` 100%
  coverage; ruff format/check clean; mypy clean. Added a `dev` Docker stage (pytest, ruff,
  mypy) so gates run without local Python.
- Step 4: TDD red (`cannot import name 'create_app'`) → green: 16 tests, 100% coverage; ruff
  and mypy clean. Runtime image 396 MB builds; `docker compose up -d web redis` with the real
  `.env` → both `healthy`, `GET /health` → `200 {"status":"ok"}`, web runs as `appuser`,
  memory web 82 MiB / 384 MiB, redis 6 MiB / 128 MiB.
- Step 5: TDD red → green: 20 schema tests (31 total with config), `app/schemas.py` 100%
  coverage; ruff and mypy clean. 10 document types (invoice, receipt, purchase_order, quote,
  bank_statement, contract, payslip, resume, report, other) mapped to 6 sections; the Gemini
  SDK accepts `DocumentSchema` as `response_schema` (real API call comes in step 9).
- Step 6: `DATABASE_URL` moved to the session pooler (5432); connection verified with SSL to
  PostgreSQL 17.6. TDD red → green: 42 unit tests + 2 integration tests against the real
  Supabase (table created, RLS on, insert/read/delete round-trip), 93% total coverage; ruff and
  mypy clean. `python -m app.db` in the runtime image creates the table: 10 columns, 0 rows,
  `relrowsecurity = true`. `config.py` now accepts the `postgresql://` URL as Supabase shows it.
- Step 7: TDD red → green: 19 storage tests (61 total), `app/storage.py` 100% coverage; ruff
  and mypy clean. A 50 MB upload is written to disk with a peak of 199 KB of Python memory
  (64 KB chunks). Rejects non-PDF bytes and oversize files, leaving no partial file; `.part` +
  rename so the worker never sees half-written files; `delete_file()` refuses paths outside
  the upload dir.
- Step 8: TDD red → green: 7 extraction tests (68 total), `app/pdf_text.py` 100% coverage; ruff
  and mypy clean. Test PDFs are generated in `tests/conftest.py` (no new dependency, Latin-1
  accents round-trip). 300-page PDF: full read peaks at 81 MB RSS; with the default 60,000-char
  cap only 9 pages are parsed (1.1 s). Scanned PDFs (< 20 visible chars) raise
  `NoTextLayerError`; corrupted files raise `UnreadablePdfError`.
- Step 9: TDD red → green: 25 LLM unit tests with fake clients (no cost, no network), 93 unit
  tests total, 96% coverage; ruff and mypy clean. 3 integration tests against the real Gemini
  API (`gemini-3.1-flash-lite`) pass: Spanish invoice (total 119000 CLP, dates, RUTs, line
  items), English contract (2 parties, auto-renewal, 60-day notice, USD) and bank statement
  (only the last 4 digits kept). Real cost: 302 input + 371 output tokens ≈ USD 0.0006 per
  invoice. Every provider output goes through `parse_response()` (Pydantic); rate limits,
  5xx and network errors raise `LLMTransientError` (retry), everything else
  `LLMExtractionError` (fail). The dev image now installs all extras so OpenAI is tested.
- Step 10: TDD red → green: 9 task tests run through `apply()` (104 unit tests total, 96%
  coverage; `tasks.py` 98%); ruff and mypy clean. Real end to end with web + worker + redis and
  the real Gemini and Supabase: ephemeral run PENDING → STARTED → SUCCESS in 4.5 s, no row in
  Supabase; persistent run in 7.8 s with the row saved (then deleted); both results in Redis
  with a ~3600 s TTL; `/tmp_uploads` empty afterwards. Memory: worker 171 MiB / 768 MiB, web
  82 MiB / 384 MiB, redis 7 MiB / 128 MiB. Retries only `LLMTransientError` and
  `OperationalError` (10 s, 20 s, 40 s backoff, max 3) and keeps the PDF only while a retry is
  pending.
- Step 11: TDD red → green: 17 export tests (121 total, 96% coverage; `export.py` 99%); ruff
  and mypy clean. Individual CSV: one row per line item for commercial documents (24 columns
  for an invoice), one row otherwise. Unified CSV: 64 columns derived from `DocumentSchema`,
  identical for every batch. UTF-8 with BOM; text starting with `= + - @ TAB CR` is prefixed
  with `'`, numbers never are (negative amounts stay numeric). Request payloads are validated
  (`ExportItem`, `UnifiedExportRequest`: 1 to 500 documents). Both exports are generators.
  Known limit: spreadsheets may drop leading zeros of numeric-looking text such as "004512".
- Step 12: TDD red → green: 21 web tests + 16 queue/ownership tests (155 unit tests total, 96%
  coverage); ruff and mypy clean. Tasks are tied to the browser: a random owner token in the
  signed session cookie (HttpOnly, SameSite=Lax) and `task-owner:<token>` sets in Redis db 1
  expiring with the results; any other browser gets 404. The Celery app moved to
  `app/celery_app.py`, so the web process enqueues by task name without importing pdfplumber,
  the LLM SDKs or SQLAlchemy. Real HTTP run against the stack: upload of 2 PDFs + 1 fake → 202,
  2 tasks, fake rejected; invoice pending → processing → completed in 3.2 s, contract in 1.9 s;
  Bob's requests for Alice's tasks → 404 and 404; individual CSV 1 row, unified CSV 2 rows × 64
  columns; persistent mode wrote both rows to Supabase (deleted after); `/tmp_uploads` empty;
  web 104 MiB / 384, worker 144 MiB / 768. Also fixed a compose bug: web and worker built the
  same image concurrently.
- Step 11b (added after step 12): XLSX and JSON exports next to CSV. `export.py` now builds one
  table of typed values and writes it as CSV (streamed), XLSX (XlsxWriter: typed numbers and
  dates, text via `write_string` so formulas never run, frozen header, filters) or JSON (nested,
  `ensure_ascii=False`). Routes generalized to `/export/{csv|xlsx|json}/{individual|unified}`.
  164 unit tests, 96% coverage. Real downloads from the stack: XLSX detected as "Microsoft Excel
  2007+", `004512` kept as text, totals numeric, dates typed. `openpyxl` added to the dev group
  only, to read the files back in tests.

## How to run the quality gates

```bash
docker build -f docker/Dockerfile --target dev -t pdf-process-pipeline:dev .
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev ruff check app tests
docker run --rm -v "$PWD":/src -w /src pdf-process-pipeline:dev mypy app tests
# Integration tests against the real Supabase (reads .env):
docker run --rm --env-file .env -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest -m integration
```

## Next

Step 13 — UI: Jinja2 page with a dropzone, the persistent/ephemeral toggle, live status polling,
a results table, Chart.js charts and both CSV buttons.
