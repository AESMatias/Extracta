---
type: constitution
title: pdf_process_pipeline (IDP) — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-09-24T00:00:00Z
topic: sdd
version: v2.3.0
---

# pdf_process_pipeline (IDP) — Constitution

> Version: v2.3.0 · Ratified: 2026-09-24 · Last amended: 2026-09-24
> The non-negotiable principles every rsc-sdd phase obeys. Stack mechanics live in the
> installed stack skills (`python`, `docker`, `redis`, `supabase`, `postgresdb`); this file
> ratifies the principle and points at the detail.

## 1. Stack canon

1. Python 3.12. Dependencies are managed with **Poetry**: declared in `pyproject.toml`,
   pinned in `poetry.lock`, both committed. No hand-edited `requirements.txt`.
~~2. Frameworks fixed: Flask + Jinja2 (web/UI), Celery (workers), Redis (broker), PostgreSQL on
   **Supabase** (storage), Pydantic v2 (schemas), `pdfplumber` (text extraction), `openai` SDK
   with structured outputs bound to a Pydantic schema. Changing one is a MAJOR amendment.~~
   (superseded by 18)
3. Every service runs through Docker Compose. The database is Supabase (managed), so Compose
   has no local Postgres container.

## 2. Quality bar

4. Code passes `ruff format --check` and `ruff check` with zero findings.
5. `mypy` (basic mode) passes with no errors before merge.
6. Every module has `pytest` tests; line coverage ≥ 70% on changed code.

## 3. Conventions

~~7. All code, identifiers and inline comments are in English. Explanations to the user are in
   Spanish.~~ (superseded by 24)
~~8. Commit messages carry a gitmoji + Conventional Commits (`✨ feat(scope): subject`).
   Enforced by `.rsc/gitmoji-guard.mjs`.~~ (superseded by 20)

## 4. Branching & shipping

9. Work happens on a branch off `main`; it merges only after `verify` passes.
10. **Git authorship is the human's.** No `Co-Authored-By` an AI, no "generated with" footer.
    Enforced at the `ship` phase.

## 5. Security & privacy floor

~~11. No secret is ever committed. `OPENAI_API_KEY` and Supabase credentials load from
    `01-TOOLS/<provider>/.env` (gitignored).~~ (superseded by 19)

## 6. Resource floor (2 GB RAM production server)

12. The Celery worker runs with `--concurrency=1`: one document at a time.
13. Every Compose service declares `deploy.resources.limits.memory`; the sum stays ≤ 1.5 GB.
14. Uploads are streamed to the `/tmp_uploads` volume in chunks; a full file is never held
    in RAM.
~~15. The worker deletes the PDF from `/tmp_uploads` immediately after its data is saved to
    the database.~~ (superseded by 21)

## 7. UX / accessibility floor

16. The upload form is keyboard-operable, and each document's status
    (Pending / Processing / Completed / Failed) is shown as text, not colour alone.

## 8. Knowledge & decisions

17. Every significant decision is appended to `02-DOCS/wiki/sdd/decisions.md` (date, options,
    why). The constitution is the highest-order decision record.

## 9. Amendments v2.0.0

18. Frameworks fixed: Flask + Jinja2 (web/UI), Celery (workers), Redis (broker), PostgreSQL on
    **Supabase** (storage), Pydantic v2 (schemas), `pdfplumber` (text extraction). LLM
    extraction goes through one provider-agnostic interface with structured output bound to
    the Pydantic schema; the provider and model are chosen only by `LLM_PROVIDER` and
    `LLM_MODEL` in `.env`. Default: Gemini (`google-genai` SDK) on the cheapest Flash model.
    Other providers (e.g. OpenAI) are optional Poetry extras, never required dependencies.
    Changing a fixed framework is a MAJOR amendment.
19. No secret is ever committed. Secrets load from the root `.env` (gitignored), which Docker
    Compose reads; `.env.sample` documents every variable with empty or placeholder values.

## 10. Amendments v2.1.0

20. Commit messages carry a gitmoji + Conventional Commits, and the subject is a descriptive
    sentence starting with an imperative verb that says what the change does
    (`✨ feat(config): add validated settings loaded from .env`). Commits are referred to by
    that description, never by hash alone. Gitmoji enforced by `.rsc/gitmoji-guard.mjs`.

## 11. Amendments v2.2.0

21. The worker deletes the PDF from `/tmp_uploads` when its task finishes — after success or
    after the final failed attempt — whether or not the data was saved to the database
    (`finally` block). Only a pending retry may keep the file.
22. Ephemeral mode (`save_to_db=false`) never writes document data to PostgreSQL. Results live
    only in the Redis result backend and expire after a configured TTL.
23. Every CSV export escapes cells that start with `=`, `+`, `-`, `@`, tab or carriage return
    (CSV/formula injection), and exported data is validated against `DocumentSchema` first.

## 12. Amendments v2.3.0

24. Everything committed to the repository is in English: code, identifiers, comments,
    docstrings, README, project docs, `.env.sample` and commit messages. Only the chat with the
    owner is in Spanish. Spanish text may appear inside English artifacts only as data (e.g.
    document names such as "boleta" or "liquidación de sueldo" that the LLM must recognize).
    Files generated by the rsc harness (`GEMINI.md`, `.claude/rsc-bootstrap.mjs`) are exempt.

## Definition of Done (the merge bar `verify` runs against)

A change ships only when ALL hold:

- [ ] Dependencies changed only through Poetry; lockfile committed (principle 1).
- [ ] Ruff format + lint clean (principle 4).
- [ ] mypy passes (principle 5).
- [ ] Tests pass; coverage ≥ 70% on changed code (principle 6).
- [ ] Everything committed is in English; gitmoji commit with a descriptive imperative subject (principles 20, 24).
- [ ] On a branch, authored by the human (principles 9-10).
- [ ] No secret committed; `.env.sample` updated for new variables (principle 19).
- [ ] RAM/disk rules intact: concurrency 1, memory limits, streaming, cleanup (principles 12-14, 21-22).
- [ ] UI floor met where UI changed (principle 16).
- [ ] CSV exports escaped and validated (principle 23).
- [ ] Significant decisions logged (principle 17).

## Amendment log (append-only)

| Date | Version | Change | Why |
|------|---------|--------|-----|
| 2026-09-24 | v1.0.0 | Ratified initial constitution. | Project kickoff. |
| 2026-09-24 | v2.0.0 | Struck 2 → 18: OpenAI SDK replaced by a provider-agnostic LLM layer, Gemini Flash by default. Struck 11 → 19: secrets in root `.env`. | Owner prefers Gemini credits and a model switchable from `.env`; Compose reads root `.env`. |
| 2026-09-24 | v2.1.0 | Struck 8 → 20: commit subjects must be descriptive imperative sentences; commits referenced by description, not hash. | Owner reviews step by step and a bare hash tells nothing. |
| 2026-09-24 | v2.2.0 | Struck 15 → 21 (delete PDF in all outcomes); added 22 (ephemeral mode) and 23 (safe CSV export). | New feature: ephemeral processing and CSV export. |
| 2026-09-24 | v2.3.0 | Struck 7 → 24: every repository artifact in English; Spanish only in the chat. | Owner clarified after a README was written in Spanish. |
