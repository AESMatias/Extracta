---
type: constitution
title: pdf_process_pipeline (IDP) — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-09-24T00:00:00Z
topic: sdd
version: v1.0.0
---

# pdf_process_pipeline (IDP) — Constitution

> Version: v1.0.0 · Ratified: 2026-09-24 · Last amended: 2026-09-24
> The non-negotiable principles every rsc-sdd phase obeys. Stack mechanics live in the
> installed stack skills (`python`, `docker`, `redis`, `supabase`, `postgresdb`); this file
> ratifies the principle and points at the detail.

## 1. Stack canon

1. Python 3.12. Dependencies are managed with **Poetry**: declared in `pyproject.toml`,
   pinned in `poetry.lock`, both committed. No hand-edited `requirements.txt`.
2. Frameworks fixed: Flask + Jinja2 (web/UI), Celery (workers), Redis (broker), PostgreSQL on
   **Supabase** (storage), Pydantic v2 (schemas), `pdfplumber` (text extraction), `openai` SDK
   with structured outputs bound to a Pydantic schema. Changing one is a MAJOR amendment.
3. Every service runs through Docker Compose. The database is Supabase (managed), so Compose
   has no local Postgres container.

## 2. Quality bar

4. Code passes `ruff format --check` and `ruff check` with zero findings.
5. `mypy` (basic mode) passes with no errors before merge.
6. Every module has `pytest` tests; line coverage ≥ 70% on changed code.

## 3. Conventions

7. All code, identifiers and inline comments are in English. Explanations to the user are in
   Spanish.
8. Commit messages carry a gitmoji + Conventional Commits (`✨ feat(scope): subject`).
   Enforced by `.rsc/gitmoji-guard.mjs`.

## 4. Branching & shipping

9. Work happens on a branch off `main`; it merges only after `verify` passes.
10. **Git authorship is the human's.** No `Co-Authored-By` an AI, no "generated with" footer.
    Enforced at the `ship` phase.

## 5. Security & privacy floor

11. No secret is ever committed. `OPENAI_API_KEY` and Supabase credentials load from
    `01-TOOLS/<provider>/.env` (gitignored).

## 6. Resource floor (2 GB RAM production server)

12. The Celery worker runs with `--concurrency=1`: one document at a time.
13. Every Compose service declares `deploy.resources.limits.memory`; the sum stays ≤ 1.5 GB.
14. Uploads are streamed to the `/tmp_uploads` volume in chunks; a full file is never held
    in RAM.
15. The worker deletes the PDF from `/tmp_uploads` immediately after its data is saved to
    the database.

## 7. UX / accessibility floor

16. The upload form is keyboard-operable, and each document's status
    (Pending / Processing / Completed / Failed) is shown as text, not colour alone.

## 8. Knowledge & decisions

17. Every significant decision is appended to `02-DOCS/wiki/sdd/decisions.md` (date, options,
    why). The constitution is the highest-order decision record.

## Definition of Done (the merge bar `verify` runs against)

A change ships only when ALL hold:

- [ ] Dependencies changed only through Poetry; lockfile committed (principle 1).
- [ ] Ruff format + lint clean (principle 4).
- [ ] mypy passes (principle 5).
- [ ] Tests pass; coverage ≥ 70% on changed code (principle 6).
- [ ] English code, gitmoji commit (principles 7-8).
- [ ] On a branch, authored by the human (principles 9-10).
- [ ] No secret committed (principle 11).
- [ ] RAM/disk rules intact: concurrency 1, memory limits, streaming, cleanup (principles 12-15).
- [ ] UI floor met where UI changed (principle 16).
- [ ] Significant decisions logged (principle 17).

## Amendment log (append-only)

| Date | Version | Change | Why |
|------|---------|--------|-----|
| 2026-09-24 | v1.0.0 | Ratified initial constitution. | Project kickoff. |
