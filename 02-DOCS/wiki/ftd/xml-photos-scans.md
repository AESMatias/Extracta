---
title: XML e-invoices, photos and scanned PDFs
status: done
updated: 2026-09-26
---

# XML e-invoices, photos and scanned PDFs

## Intent

Accept the formats invoices really come in: the legal XML of Latin American and European
e-invoicing, phone photos of receipts, and scanned PDFs (which used to fail), for every plan,
without loading the 2 GB server with OCR.

## Decisions (owner)

- OCR by Gemini's vision, for every plan: it costs about the same per page as text.
- An XML file or a photo counts as one page.
- No XML export: a legal e-invoice needs the issuer's signature and the tax authority's stamp,
  and a data XML would repeat the JSON export.

## Design

`app/formats.py` sniffs the format from the first bytes (PDF, XML, JPEG, PNG, WebP, HEIC) and
`save_stream()` stores it under that extension. On upload a PDF is checked and counted as before;
XML and photos are validated (safe parse, pixel cap) and cost one page. In the worker: PDF text
as before; a PDF with no text, or with most pages without text, is sent whole to the model
(inline up to 14 MB, else the Files API, deleted after the call); XML is parsed with defusedxml
(DTDs forbidden), stripped of `Signature` elements and base64 blobs, compacted and sent as text;
photos are decoded under a 60 MP cap, turned upright, shrunk to 2048 px and re-encoded as JPEG
without metadata. Providers gained `extract_file(data, mime_type)` (Gemini inline or Files API,
OpenAI image or file part). Results carry `source`: text, xml, photo or scan.

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Format detection and storage | `tests/test_formats.py` (16 sniff cases, extensions, 2 MB XML cap); `tests/test_storage.py` sweep | ✅ |
| 2 | Safe XML | billion laughs, external entity, malformed refused; DTE signature and CFDI seal removed, long descriptions kept; mutation check: disabling the DTD ban fails the test | ✅ |
| 3 | Safe photos | GPS removed (mutation check: keeping EXIF fails the test), orientation, transparency, HEIC, pixel bombs and broken files refused | ✅ |
| 4 | Pipeline and upload route | `tests/test_tasks.py` (scan, mostly-scan, text, XML, photo, broken photo refunded); `tests/test_web.py` (1 page each, hostile files refused on upload) | ✅ |
| 5 | Providers | `tests/test_llm.py` (Gemini inline and Files API with deletion, OpenAI parts) | ✅ |
| 6 | Real Gemini | photo $0.00096, scanned PDF $0.00085, DTE $0.00070, CFDI $0.00062, UBL $0.00058: every total exact | ✅ |
| 7 | Runtime image | HEIC decode and defusedxml work in `pdf-process-pipeline:latest` (414 MB) | ✅ |
| 8 | Frontend, legal texts, errors (en/es) | tsc and eslint clean; landing checked in a browser | ✅ |
