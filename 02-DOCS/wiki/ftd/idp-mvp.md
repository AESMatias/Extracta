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
| 7 | Streaming upload storage | `app/storage.py` + test | Large file written in chunks; RAM stays flat | ⏳ next |
| 8 | PDF text extraction | `app/pdf_text.py` + test | Text extracted from a sample PDF | ⬜ |
| 9 | LLM layer | `app/llm/{base,gemini,openai,factory}.py` + tests | Factory picks provider from `.env`; Gemini returns a `DocumentSchema` | ⬜ |
| 10 | Celery task | `app/tasks.py` + test | `save_to_db` true → row in Supabase; false → no DB call; both return the data (Redis backend, TTL); PDF deleted in every outcome | ⬜ |
| 11 | CSV export | `app/export.py` + test | Individual (one doc, line items as rows) and unified (one row per doc) CSV; formula injection escaped | ⬜ |
| 12 | Web routes | `app/web/routes.py` + tests | `POST /upload` (+ `save_to_db`) → task ids; `GET /tasks/<id>` → status + result; `POST /export/csv/individual` and `/unified` stream CSV | ⬜ |
| 13 | UI | `app/web/templates/`, `app/web/static/` | Dropzone + mode toggle + polling + results table + Chart.js charts + both CSV buttons | ⬜ |
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

Step 7 — `app/storage.py`: stream uploaded PDFs to `/tmp_uploads` in chunks, enforce
`MAX_UPLOAD_MB`, and prove RAM stays flat with a large file.
