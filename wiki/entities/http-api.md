---
title: HTTP API
type: entity
tags: [fastapi, routes, api]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/main.py, backend/routers/settings.py]
---

FastAPI app defined in `backend/main.py`. CORS is restricted to the Vite dev server origins; the app assumes local-only deployment.

## Routes

| Verb | Path | Handler | Purpose |
|---|---|---|---|
| `GET` | `/` | `read_root` | Welcome string. |
| `GET` | `/health` | `health_check` | Liveness probe. |
| `GET` | `/api/search/lcsc?q=` | `search_lcsc` | Proxy to [[entities/lcsc-service]]; returns `List[Part]`. |
| `POST` | `/api/generate/schematic?mpn=&supplier_id=` | `generate_schematic` | Writes a `.kicad_sch` via [[entities/schematic-service]] and streams the file. *Does not* accept pins — that path is reserved for the AI tool. |
| `GET` | `/api/download/{filename}` | `download_file` | Serves `generated_schematics/{filename}` with a `commonpath`-based traversal guard (`backend/main.py:107`). |
| `POST` | `/api/chat` | `chat` | Drives the [[entities/ai-service]] tool loop. |
| `GET` | `/api/settings` | settings router | Returns current env-var config as a `Settings` JSON. |
| `POST` | `/api/settings` | settings router | Mirrors request fields into `os.environ` and rewrites `.env`. |

## Cross-cutting

- **Global exception handler** (`backend/main.py:23`) turns any uncaught exception into a generic 500 JSON, logging the traceback server-side. Do not let sensitive details leak into responses.
- **System prompt** for `/api/chat` is built inline at `backend/main.py:127` and prepended only if the client didn't already include a `system` role. If you add a new tool, update the prompt here so the model knows to use it.
- **CORS origins** are hardcoded in `backend/main.py:46` (`localhost:5173`, `127.0.0.1:5173`).

## Known gaps

- `POST /api/generate/schematic` has no `pins` parameter yet. The frontend "Generate Schematic" button therefore always uses the library → placeholder fallback. To exercise datasheet-derived pinouts today, go through chat.
- `ChatRequest` allows `extra = "allow"` on messages so LiteLLM tool-call/tool-result payloads pass through. If you change message shape, be careful — validation is intentionally loose here.
