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
`DocumentSchema` with an LLM (Gemini by default, switchable via `.env`), saves it to Supabase
and deletes the PDF. The owner is learning Flask, so work advances one reviewed step at a time.

## Scope

- In: Flask + Jinja2 UI, streaming uploads, Celery + Redis queue, Supabase storage,
  provider-agnostic LLM layer, Docker Compose with memory limits, tests.
- Not now: authentication, multi-tenant users, OCR for scanned PDFs, VPS deployment (a later
  feature).

## Checklist

Each step = one file (or a tiny group) + its tests, reviewed and committed before the next.

| # | Step | Files | Proof it is done | Status |
|---|------|-------|------------------|--------|
| 0 | Harness + local tooling | `.rsc.json`, Colima/Docker | `RSC_ONBOARDING_READY`; `docker compose version` | ✅ |
| 1 | Base configuration | `pyproject.toml`, `docker-compose.yml`, `.env.sample` | `docker compose config` OK | ✅ `3713af3` |
| 2 | Docker image | `docker/Dockerfile`, `.dockerignore`, `poetry.lock` | Dependency stage builds and imports; Trivy scan reviewed | ✅ `eae6313` |
| 3 | Settings | `app/config.py` + test | Missing/invalid `.env` values fail at startup with a clear error | ⏳ next |
| 4 | Flask app factory + health check | `app/__init__.py` + test | Full image builds; `docker compose up web redis` → `GET /health` 200 | ⬜ |
| 5 | Extraction schema | `app/schemas.py` + test | `DocumentSchema` validates/rejects sample payloads | ⬜ |
| 6 | Database | `app/db.py`, `app/models.py` + test | `documents` table created in Supabase; insert/read round-trip | ⬜ |
| 7 | Streaming upload storage | `app/storage.py` + test | Large file written in chunks; RAM stays flat | ⬜ |
| 8 | PDF text extraction | `app/pdf_text.py` + test | Text extracted from a sample PDF | ⬜ |
| 9 | LLM layer | `app/llm/{base,gemini,openai,factory}.py` + tests | Factory picks provider from `.env`; Gemini returns a `DocumentSchema` | ⬜ |
| 10 | Celery task | `app/tasks.py` + test | extract → LLM → save → delete PDF; status transitions recorded | ⬜ |
| 11 | Web routes | `app/web/routes.py` + tests | Upload returns task ids; status endpoint returns JSON | ⬜ |
| 12 | UI | `app/web/templates/`, `app/web/static/` | Dropzone + polling + results table in the browser | ⬜ |
| 13 | Verify | — | ruff, mypy, pytest ≥ 70% coverage all green | ⬜ |
| 14 | End-to-end + merge | — | Batch of real PDFs processed under the 2 GB limits; merged to `main` | ⬜ |

## Evidence

- Step 0: `RSC_ONBOARDING_READY 63371e3d…`; Docker 29.8.1 / Compose 5.5.1 on Colima (2 CPU, 2 GB).
- Step 1: `docker compose config` → OK; limits web 384M, worker 768M, redis 128M (sum 1280M).
- Step 2: builder stage imports Flask 3.1.3, Celery 5.6.3, Pydantic 2.13.5, google-genai;
  `POETRY_EXTRAS=openai` adds openai 3.19.2. Trivy on `poetry.lock`: 0 vulnerabilities.
  Trivy on `python:3.12-slim` (Debian 13.7): HIGH findings only in OS packages with no fix
  released upstream — see decision 2026-09-24 in `02-DOCS/wiki/sdd/decisions.md`.

## Next

Step 3 — `app/config.py`: load and validate `.env` with `pydantic-settings`.
