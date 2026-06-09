# TripleT KiCad Agent

An AI-powered engineering assistant that bridges the gap between high-level system requirements and physical PCB design. The user chats with an LLM that can search parts on LCSC/JLCPCB, apply verified circuit patterns, and emit real KiCad 9 schematic files.

The authoritative roadmap lives in [`PLANNING.md`](./PLANNING.md).

## Status

- **Phase 1 — Part & Datasheet Expert (MVP):** complete. Chat, LCSC search, add-to-BOM, basic `.kicad_sch` generation.
- **Phase 2 — Agentic Interface:** complete. Multi-turn tool-calling loop, model selection in Settings, downloadable output.
- **Phase 2.5 — Pattern Library:** complete. Executable patterns (LDO, USB-C input, I²C pull-ups, MCU reset) with BM25 retrieval and `lookup_pattern` / `apply_pattern` tools.
- **Phase 3 — Symbol Engineer:** complete. Library reuse via `sym-lib-table`, procedural symbol generation, datasheet PDF fetching (`pdfplumber`), and the `extract_pinout` tool that turns a datasheet URL into a validated `PinSpec[]` for `generate_schematic`.
- **Phase 4 — Circuit Designer:** not started.

## Stack

**Backend** (`backend/`)

- Python `>= 3.14`, managed with [`uv`](https://docs.astral.sh/uv/).
- FastAPI + Uvicorn for the HTTP surface.
- [LiteLLM](https://docs.litellm.ai/) as a provider-agnostic wrapper over OpenAI, Anthropic, and Gemini.
- `httpx` for outbound calls to the jlcsearch/LCSC proxy.
- `rank-bm25` for pattern retrieval.
- `kicad-sch-api` for schematic mutation inside pattern `apply()` callbacks; a hand-rolled parser in `backend/services/kicad_libs.py` handles `sym-lib-table` lookups.
- `pytest` + `pytest-asyncio`.

**Frontend** (`frontend/`)

- React 19 + TypeScript 5.9 (strict) on [`rolldown-vite`](https://github.com/vitejs/rolldown-vite).
- Tailwind CSS v4 via `@tailwindcss/vite`.
- `axios` for API calls, `react-markdown` for rendering assistant replies, `lucide-react` for icons.
- State is a single `BOMContext` (in-memory only).

## Architecture

### Backend layout

| Path | Responsibility |
|---|---|
| `backend/main.py` | FastAPI app, CORS, route registration. |
| `backend/routers/settings.py` | `GET`/`POST /api/settings` — reads and writes env vars, persists to `.env`. |
| `backend/services/ai.py` | `AIService` — bounded multi-turn tool loop over LiteLLM. |
| `backend/services/tools.py` | Tool JSON schemas and the `execute_tool()` dispatcher. |
| `backend/services/lcsc.py` | Part search against `jlcsearch.tscircuit.com`. |
| `backend/services/schematic.py` | Writes `.kicad_sch` files (KiCad 9 S-expression). |
| `backend/services/symbol_resolver.py` | Picks library symbol vs procedural fallback. |
| `backend/services/kicad_libs.py` | `sym-lib-table` + `.kicad_sym` indexer. |
| `backend/services/procedural_symbol.py` | Emits a rectangle-with-pins symbol from a `PinSpec` list. |
| `backend/services/datasheet.py` | Async PDF fetch + text extraction via `pdfplumber`. |
| `backend/services/pinout.py` | Dedicated-LLM-call pinout extractor returning validated `PinSpec[]`. |
| `backend/knowledge/protocol.py` | `Pattern` protocol, `PatternMetadata` dataclass. |
| `backend/knowledge/registry.py` | Auto-discovering `PatternRegistry` + `PatternRetriever` (BM25). |
| `backend/knowledge/patterns/` | Seed patterns: `ldo_regulator`, `usb_c_input`, `i2c_pullups`, `mcu_reset`. |
| `backend/tests/` | `pytest` suite. |

### HTTP API

| Verb | Route | Purpose |
|---|---|---|
| `GET` | `/` | Health/welcome string. |
| `GET` | `/health` | `{"status":"ok"}`. |
| `GET` | `/api/search/lcsc?q=` | Proxy to jlcsearch; returns `Part[]`. |
| `POST` | `/api/generate/schematic?mpn=&supplier_id=` | Generates a single-component `.kicad_sch` and streams it back. |
| `GET` | `/api/download/{filename}` | Serves files from `generated_schematics/` (path-traversal guarded). |
| `POST` | `/api/chat` | Runs the AI tool loop over the supplied message thread. |
| `GET` / `POST` | `/api/settings` | Reads/writes the current env-var configuration. |

### Frontend layout

| File | Responsibility |
|---|---|
| `frontend/src/main.tsx` | Entry point, wraps `<App>` in `<BOMProvider>`. |
| `frontend/src/App.tsx` | Tab layout (Home / BOM / Settings). |
| `frontend/src/components/ChatInterface.tsx` | Chat panel; posts to `/api/chat`, renders Markdown, injects BOM context. |
| `frontend/src/components/PartSearch.tsx` | LCSC search, per-result "Generate Schematic" and "Add to BOM". |
| `frontend/src/components/BOMPage.tsx` | BOM table, delete, CSV export. |
| `frontend/src/components/SettingsPage.tsx` | Form bound to `/api/settings`. |
| `frontend/src/context/BOMContext.tsx` | In-memory BOM state. |

The frontend uses a Vite proxy configured to target the backend port dynamically loaded from `.env` (default is port 8080).

## Running locally

Backend:

```bash
uv sync
cp .env.example .env   # add at least one provider API key
uv run python -m backend.main
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

With both running, open the Vite URL (default `http://localhost:5173`). The backend must be reachable at `http://localhost:8000`.

## Configuration

### `.env`

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI provider key. | — |
| `ANTHROPIC_API_KEY` | Anthropic provider key. | — |
| `GEMINI_API_KEY` | Google Gemini provider key. | — |
| `DEFAULT_AI_MODEL` | LiteLLM model string (e.g. `gemini/gemini-3-pro`, `gpt-4o`, `anthropic/claude-sonnet-4-6`). | `gpt-4o` if unset |
| `AI_MAX_TOOL_TURNS` | Ceiling on tool-call turns per `/api/chat` request. | `6` |

### Settings page (writes back to `.env`)

In addition to the variables above, the Settings UI persists KiCad library paths used by the symbol resolver:

| Variable | Purpose |
|---|---|
| `KICAD_SYM_LIB_TABLE` | Absolute path to the user's `sym-lib-table`; enables library-symbol reuse. |
| `KICAD_SYMBOL_DIR` | Root symbol library directory (plumbed through Settings; read by the resolver when needed). |
| `KICAD_FOOTPRINT_DIR` | Root footprint library directory. |

## Testing

```bash
uv run pytest backend/tests/
```

The suite lives under `backend/tests/` and covers AI service loop behaviour, search, pattern registry + retrieval, the procedural symbol generator, schematic emission, `sym-lib-table` parsing, error handling, and security (prompt injection, path traversal, settings).

Frontend typechecking:

```bash
cd frontend
npm install
npx tsc -b --noEmit
```

There is one known pre-existing TypeScript/lint issue in `frontend/src/components/ChatInterface.tsx` (untyped `catch` clause) that predates recent feature work.
