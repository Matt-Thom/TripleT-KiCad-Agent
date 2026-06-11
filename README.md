# TripleT KiCad Agent

An AI-powered engineering assistant that bridges the gap between high-level system requirements and physical PCB design. The user chats with an LLM that can search parts on LCSC/JLCPCB, apply verified circuit patterns, plan a system architecture, build a netlist, run electrical rules checks, and emit a complete KiCad 9 project ready for board layout.

The authoritative roadmap lives in [`PLANNING.md`](./PLANNING.md).

## Status

- **Phase 1 — Part & Datasheet Expert (MVP):** complete. Chat, LCSC search, add-to-BOM, basic `.kicad_sch` generation.
- **Phase 2 — Agentic Interface:** complete. Multi-turn tool-calling loop, model selection in Settings, downloadable output.
- **Phase 2.5 — Pattern Library:** complete. Executable patterns (LDO, USB-C input, I²C pull-ups, MCU reset) with BM25 retrieval and `lookup_pattern` / `apply_pattern` tools.
- **Phase 2.6 — Project Persistence:** complete. Async SQLite (SQLModel) behind REST endpoints for projects, BOM, and chat history.
- **Phase 3 — Symbol Engineer:** complete. Library reuse via `sym-lib-table`, procedural symbol generation, datasheet PDF fetching (`pdfplumber`), and the `extract_pinout` tool that turns a datasheet URL into a validated `PinSpec[]`.
- **Phase 4 — Circuit Designer:** complete. System architecture planner (block diagram), structural Schematic/Netlist IR, local ERC, net-label connectivity, footprint auto-assignment from packages, and IR compilation into a complete KiCad project (`.kicad_pro` + `.kicad_sch` + generated symbol library + `sym-lib-table`). The Design Board dashboard visualizes blocks, netlist, and ERC results.
- **Phase 5 — PCB Layout:** not started. Board placement/routing happens in KiCad ("Update PCB from Schematic" works out of the box since footprints are pre-assigned). A thin `kicad-cli` wrapper already exposes native ERC, netlist/BOM/PDF export, and Gerber/drill export for routed boards when KiCad is installed server-side.

## Stack

**Backend** (`backend/`)

- Python `>= 3.12`, managed with [`uv`](https://docs.astral.sh/uv/).
- FastAPI + Uvicorn for the HTTP surface.
- [LiteLLM](https://docs.litellm.ai/) as a provider-agnostic wrapper over OpenAI, Anthropic, and Gemini (async `acompletion`).
- SQLModel + aiosqlite for project persistence (`data/triplet.db`).
- `httpx` for outbound calls to the jlcsearch/LCSC proxy.
- `rank-bm25` for pattern retrieval.
- `kicad-sch-api` for schematic emission (components, net labels, footprints); a hand-rolled parser in `backend/services/kicad_libs.py` handles `sym-lib-table` lookups.
- `pytest` + `pytest-asyncio`.

**Frontend** (`frontend/`)

- React 19 + TypeScript 5.9 (strict) on [`rolldown-vite`](https://github.com/vitejs/rolldown-vite).
- Tailwind CSS v4 via `@tailwindcss/vite`.
- `axios` for API calls, `react-markdown` for rendering assistant replies, `lucide-react` for icons.
- State is a single `BOMContext` backed by the projects API.

## Architecture

### Backend layout

| Path | Responsibility |
|---|---|
| `backend/main.py` | FastAPI app, CORS, route registration, chat system prompt (board-design workflow). |
| `backend/db.py` | Async SQLite engine/session factory. |
| `backend/routers/settings.py` | `GET`/`POST /api/settings` — reads and writes env vars, persists to `.env`. |
| `backend/routers/projects.py` | Projects, BOM, messages, block diagram, schematic IR, ERC, compile. |
| `backend/models/project.py` | `Project`, `BomItem`, `Message`, `BlockDiagram`, `SchematicIR` tables. |
| `backend/models/schematic_ir.py` | Pydantic schemas for the block diagram and netlist IR (incl. `package`/`footprint`). |
| `backend/services/ai.py` | `AIService` — bounded multi-turn async tool loop over LiteLLM. |
| `backend/services/tools.py` | Tool JSON schemas and the `execute_tool()` dispatcher (project-scoped). |
| `backend/services/lcsc.py` | Part search against `jlcsearch.tscircuit.com` (incl. datasheet URLs). |
| `backend/services/schematic.py` | Emits `.kicad_sch` files and complete KiCad projects from the IR. |
| `backend/services/erc.py` | Local electrical rules checker over the netlist IR. |
| `backend/services/footprints.py` | Package-string → KiCad footprint ID mapping. |
| `backend/services/fabrication.py` | `kicad-cli` wrapper: native ERC, netlist/BOM/PDF, Gerber/drill. |
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
| `GET` | `/api/search/lcsc?q=` | Proxy to jlcsearch; returns `Part[]` incl. `datasheet_url`. |
| `POST` | `/api/generate/schematic?mpn=&supplier_id=` | Generates a single-component `.kicad_sch` and streams it back. |
| `GET` | `/api/download/{filename}` | Serves files from `generated_schematics/` (path-traversal guarded). |
| `POST` | `/api/chat` | Runs the AI tool loop; accepts optional `project_id`. |
| `GET`/`POST` | `/api/settings` | Reads/writes the current env-var configuration. |
| `GET`/`POST` | `/api/projects` | List/create projects (a Default project is auto-created). |
| `GET`/`POST`/`PUT`/`DELETE` | `/api/projects/{id}/bom[/{item_id}]` | BOM CRUD. |
| `GET`/`POST` | `/api/projects/{id}/messages` | Chat history. |
| `GET`/`POST` | `/api/projects/{id}/block-diagram` | Logical architecture blocks + interconnects. |
| `GET`/`POST` | `/api/projects/{id}/schematic-ir` | Structural netlist IR (components, nets). |
| `GET` | `/api/projects/{id}/erc` | Run the local ERC over the stored IR. |
| `POST` | `/api/projects/{id}/schematic-ir/compile` | Compile the IR into a KiCad project; returns all artifact download links. |

### Agent tools

`search_lcsc`, `lookup_pattern`, `apply_pattern`, `extract_pinout`, `generate_schematic`, `generate_multi_component_schematic`, `update_block_diagram`, `get_block_diagram`, `update_schematic_ir`, `get_schematic_ir`, `run_erc`, `compile_schematic_ir`, `export_fabrication_outputs`.

The chat system prompt drives the board-design workflow: architect (blocks) → source (parts) → pinout (datasheets) → connect (netlist IR) → verify (ERC) → compile (KiCad project) → fabricate (optional, needs `kicad-cli`).

### Frontend layout

| File | Responsibility |
|---|---|
| `frontend/src/main.tsx` | Entry point, wraps `<App>` in `<BOMProvider>`. |
| `frontend/src/App.tsx` | Tab layout (Home / Design Board / BOM / Settings). |
| `frontend/src/components/ChatInterface.tsx` | Chat panel; posts to `/api/chat` with the active project, renders Markdown, injects BOM context. |
| `frontend/src/components/Dashboard.tsx` | Design Board: block diagram, netlist IR, live ERC, compile-to-KiCad with per-artifact downloads. |
| `frontend/src/components/PartSearch.tsx` | LCSC search with package + datasheet links, per-result "Generate Schematic" and "Add to BOM". |
| `frontend/src/components/BOMPage.tsx` | BOM table, delete, CSV export. |
| `frontend/src/components/SettingsPage.tsx` | Form bound to `/api/settings`. |
| `frontend/src/context/BOMContext.tsx` | BOM state backed by `/api/projects/{id}/bom`. |

The frontend uses a Vite proxy configured to target the backend port dynamically loaded from `.env` (default is port 8080).

## Running locally

Backend:

```bash
uv sync
cp .env.example .env   # add at least one provider API key
uv run python -m backend.main
```

> **Note on Python versions:** the project supports Python ≥ 3.12. Keep `uv` itself up to date (`uv self update` or reinstall): old uv releases may resolve "latest Python" to a pre-release build (e.g. 3.14.0rc2) whose typing internals break pydantic at import time.

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

With both running, open the Vite URL (default `http://localhost:5173`).

### From schematic to a physical board

1. Chat: "design me a 3.3 V sensor board with an STM32 and a BME280" — the agent plans blocks, picks parts, extracts pinouts, builds the netlist, runs ERC, and compiles.
2. Download the compiled project (or grab it from the Design Board tab) and open the `.kicad_pro` in KiCad 9.
3. Footprints are pre-assigned where the package was recognized; run **Tools → Update PCB from Schematic**, place, route, and run DRC in KiCad.
4. If `kicad-cli` is installed on the server, the agent's `export_fabrication_outputs` tool produces KiCad's native ERC report, netlist, BOM CSV, PDF, and — once a routed `.kicad_pcb` exists — Gerber/drill files.

## Configuration

### `.env`

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI provider key. | — |
| `ANTHROPIC_API_KEY` | Anthropic provider key. | — |
| `GEMINI_API_KEY` | Google Gemini provider key. | — |
| `DEFAULT_AI_MODEL` | LiteLLM model string (e.g. `gemini/gemini-3-pro`, `gpt-4o`, `anthropic/claude-sonnet-4-6`). | `gpt-4o` if unset |
| `AI_MAX_TOOL_TURNS` | Ceiling on tool-call turns per `/api/chat` request. | `24` |
| `PORT` | Backend API port. | `8080` |

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

The suite lives under `backend/tests/` and covers the AI loop, search mapping (incl. datasheet URLs), pattern registry + retrieval, procedural symbols, schematic emission (labels, footprints, project artifacts), footprint mapping, the fabrication wrapper, IR persistence, ERC, `sym-lib-table` parsing, error handling, and security (prompt injection, path traversal, settings).

Frontend typechecking:

```bash
cd frontend
npm install
npx tsc -b --noEmit
```
