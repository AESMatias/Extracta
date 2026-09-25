---
type: feature
title: Per-page pricing, page packs, i18n, light/dark themes and landing redesign
tags: [ftd, billing, frontend, i18n, legal]
branch: feat/project-skeleton
---

# Per-page pricing, page packs, i18n, light/dark themes and landing redesign

## Intent

Charge per page instead of per document, sell pay-as-you-go page packs next to the monthly
subscriptions, and make the site bilingual (English/Spanish, detected from the browser), light by
default with a dark-mode button, with a security section, Terms and Privacy pages and a more
striking landing page (wind particles, a realistic invoice, 3D hovers, slanted nav hovers).

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Plans in pages, page packs, per-PDF page limits, refunds on failure | 345 unit tests (96%), migration 0004 on Supabase, integration tests | ✅ |
| 2 | Upload counts pages before processing | stack test: 2-page report counted 2, scan counted 1 and was given back | ✅ |
| 3 | Light default + dark toggle, ease-out transitions | browser check in both themes | ✅ |
| 4 | i18n en/es with detection and switch | browser check; es.ts typed against en.ts | ✅ |
| 5 | Landing: particles, invoice, steps title, centered types, security, pricing selector, 100svh first screen on phones | browser check desktop and 375 px (stats end at 812/812 px) | ✅ |
| 6 | Terms (refund clause last) and Privacy, linked from footer and sign-up | browser check | ✅ |
| 7 | Contact email and governing law reviewed by the owner | `frontend/src/lib/legal.ts` | ⏳ |

## Notes

- Security section claims only what is true: it lists ISO/IEC 27001, GDPR, OWASP ASVS and PCI
  DSS as frameworks followed, with an explicit "not certified" disclaimer.
- "Never used to train AI" is true for Extracta; Google's Gemini API only guarantees the same on
  its paid tier, so the Gemini key should have billing enabled.
- Found during testing: a `$` inside a `.env` value is expanded by Docker Compose; values with `$`
  must be single-quoted (now documented in `.env.sample`).
