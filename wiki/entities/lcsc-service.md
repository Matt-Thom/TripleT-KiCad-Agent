---
title: LCSCService — Part Search
type: entity
tags: [search, lcsc, jlcpcb, httpx]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/services/lcsc.py]
---

Async HTTP wrapper for the tscircuit community JLCPCB search proxy. Returns a normalized `Part` Pydantic model.

## What it hits

Base URL: `https://jlcsearch.tscircuit.com/api/search` (`backend/services/lcsc.py:17`). This is a community-maintained proxy — expect occasional flakiness. No API key required.

## Part model

`Part` (`backend/services/lcsc.py:5`) is the canonical cross-layer representation: MPN, manufacturer, description, price, stock, supplier part number (LCSC), supplier name (constant `"LCSC"`), optional `datasheet_url`, and a free-form `attributes` dict (Package / Basic / Preferred flags).

The frontend `types/Part.ts` mirrors this shape.

## Failure mode

Any exception during search is swallowed — `search()` returns `[]` on error (`backend/services/lcsc.py:53`). The only log is a `print` to stdout. The AI tool layer converts the empty list into a "no results, try a broader term" message (`backend/services/tools.py`).

## Known gaps

- The upstream API does not return a manufacturer name distinct from MPN prefix, so `manufacturer` is hardcoded to `"Unknown"` (line 38). Parametric data is sparse.
- `datasheet_url` is declared optional but the current mapping does not populate it from the upstream response — [[entities/pinout-extractor]] therefore relies on the model finding a URL elsewhere (often via a secondary `search_lcsc` result or user-supplied). This is worth revisiting.
