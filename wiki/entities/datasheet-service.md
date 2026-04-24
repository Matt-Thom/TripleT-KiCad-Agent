---
title: Datasheet Service — PDF fetch & text extraction
type: entity
tags: [pdf, pdfplumber, httpx, datasheet]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/services/datasheet.py, backend/tests/test_datasheet.py]
---

Thin wrapper over `httpx` + `pdfplumber`. Feeds [[entities/pinout-extractor]].

## API

- `extract_text_from_pdf_bytes(data) -> str` — sync, pure. Opens `BytesIO(data)` with `pdfplumber`, joins `page.extract_text()` across pages with newlines. Rejects input that doesn't start with the `%PDF-` magic.
- `extract_datasheet_text(url) -> str` — async. Fetches with 30s timeout and `follow_redirects=True`, then delegates to the sync parser.

## Failure modes — all raise `DatasheetError`

| Cause | Raised where |
|---|---|
| HTTP error (any `httpx.HTTPError` subclass, including status errors via `raise_for_status`) | `backend/services/datasheet.py:38` |
| Response body doesn't start with `%PDF-` (guards against HTML error pages returned with 200) | line 20 |
| `pdfplumber` parse failure (corrupt PDF, unsupported structure) | line 27 |

Callers can catch `DatasheetError` uniformly rather than distinguishing HTTP from parse errors. The pinout tool dispatcher does exactly this (`backend/services/tools.py`).

## Why pdfplumber

`pdfplumber` wraps `pdfminer.six` and adds layout-aware text extraction that tends to preserve rows in pin tables better than raw pdfminer output. It's heavier than `pypdf` (pulls in `pdfminer.six`, `pypdfium2`, `pillow`) but the quality tradeoff matters for pinout extraction, which relies on the LLM seeing coherent pin-number/name/type columns.

## Testing

Tests build hermetic minimal PDFs at runtime from hand-rolled bytes (`backend/tests/test_datasheet.py:10`) — no fixtures committed to disk, no extra deps. If the fixture builder ever breaks, trace the xref offsets carefully: they must match the byte offset of each `N 0 obj` exactly.
