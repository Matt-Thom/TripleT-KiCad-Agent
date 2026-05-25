# Wiki Index

Living knowledge base for the TripleT KiCad Agent. Source code is authoritative; this wiki is a navigational layer above it.

- **Start here:** [[overview]] — stack, architecture, directory layout, request flow.
- **Conventions:** [[schema]] — how pages are structured and when to update them.
- **Operations log:** [[log]] — chronological record of wiki changes.

## Overview

| Page | Summary |
|---|---|
| [[overview]] | One-page tour: stack, layout, request flow, config surfaces. |

## Entities (what exists and what it does)

| Page | Summary |
|---|---|
| [[entities/http-api]] | FastAPI routes in `backend/main.py` and the Settings router. |
| [[entities/ai-service]] | `AIService` — bounded multi-turn tool-calling loop over LiteLLM. |
| [[entities/lcsc-service]] | Part search against the `jlcsearch.tscircuit.com` proxy. |
| [[entities/schematic-service]] | `.kicad_sch` emission + `SymbolResolver` + procedural symbols + `sym-lib-table` indexing. |
| [[entities/datasheet-service]] | Async PDF fetch + text extraction via `pdfplumber`. |
| [[entities/pinout-extractor]] | `extract_pinout` — dedicated LLM call turning datasheet text into validated `PinSpec[]`. |
| [[entities/pattern-library]] | `PatternRegistry` + `PatternRetriever` (BM25) over executable circuit patterns. |
| [[entities/frontend]] | React 19 SPA: chat, part search, BOM, settings. |

## Concepts (how things hang together)

| Page | Summary |
|---|---|
| [[concepts/tool-calling-flow]] | How the agent chains tools across turns; datasheet → pinout → schematic. |
| [[concepts/symbol-resolution]] | Precedence: explicit pins > `sym-lib-table` match > 1-pin placeholder. |
| [[concepts/testing-strategy]] | Red/green commit discipline, pytest layout, hermetic PDF fixtures. |
| [[concepts/configuration]] | The `.env` file vs the Settings page — same storage, two surfaces. |

## Queries

(none yet — filed synthesis answers go under `wiki/queries/`)
