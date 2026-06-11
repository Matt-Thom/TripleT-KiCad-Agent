# TripleT KiCad Agent - Project Plan

## Overview
The TripleT KiCad Agent is an AI-powered engineering assistant designed to bridge the gap between high-level system requirements and physical PCB design.

## Status
**Phase:** Circuit Designer complete (planner → netlist IR → ERC → KiCad project with footprints). Next: PCB layout automation.

## Current Roadmap

### Phase 1: The "Part & Datasheet" Expert (MVP) - [COMPLETED]
*   [x] Chat Interface.
*   [x] Component Search (LCSC).
*   [x] "Add to BOM".
*   [x] Basic KiCad 9 File Generation (Placeholder).

### Phase 2: The "Agentic" Interface - [COMPLETED]
*   [x] Tool Calling (AI controls Search & Gen).
*   [x] Model Configuration (Settings).
*   [x] Downloadable Results.

### Phase 2.5: Pattern Library [COMPLETED]
*   [x] Executable patterns with metadata.
*   [x] BM25 retrieval + lookup_pattern / apply_pattern tools.
*   [x] Seed patterns: LDO, USB-C input, I2C pull-ups, MCU reset.

### Phase 2.6: Project Persistence [COMPLETED]
*   [x] Async SQLite via SQLModel (`backend/db.py`, `data/triplet.db`).
*   [x] `Project`, `BomItem`, `Message` tables (`backend/models/project.py`).
*   [x] REST endpoints for projects, BOM, and messages (`backend/routers/projects.py`):
    *   `GET/POST /api/projects`
    *   `GET/POST/DELETE /api/projects/{id}/bom[/{item_id}]`
    *   `GET/POST /api/projects/{id}/messages`
*   [x] Default project auto-created on first call, preserving the single-page UX.
*   [x] Frontend `BOMContext` now fetches and mutates through `/api/projects/{id}/bom`; a browser refresh keeps the BOM.
*   [x] `/api/chat` persists both the last user message and the assistant reply (per-project via optional `project_id`).

### Phase 3: The "Symbol Engineer" [COMPLETED]
*   [x] **Datasheet Reading:** `backend/services/datasheet.py` fetches PDFs via `httpx` and extracts text with `pdfplumber`.
*   [x] **Pinout Extractor:** `extract_pinout` AI tool runs a dedicated LLM call to turn datasheet text into a validated `PinSpec[]`. Drops pins with unknown electrical types, raises on malformed output.
*   [x] **Procedural Symbol Generator:** Python code to draw complex symbols from Pin Lists.
*   [x] **Library Reuse:** Schematic generator prefers existing symbols from the user's `sym-lib-table`; falls back to the procedural generator only when no library hit is found.
*   [x] **Chain to generate_schematic:** `generate_schematic` accepts an optional `pins` array so the agent can wire `search_lcsc` → `extract_pinout` → `generate_schematic(..., pins=...)`.
*   [x] **Datasheet URLs from search:** LCSC search requests full rows (`full=true`) and maps the `datasheet` column, so the agent can chain search → extract_pinout without asking the user for a URL.

### Phase 4: The "Circuit Designer" [COMPLETED]
*   [x] **System Architecture Planner:** `update_block_diagram` / `get_block_diagram` tools + `BlockDiagram` persistence; the Design Board dashboard renders blocks and interconnects.
*   [x] **Schematic/Netlist IR:** `update_schematic_ir` / `get_schematic_ir` tools + `SchematicIR` persistence (components, pins, nets, packages, footprints).
*   [x] **Local ERC:** `run_erc` checks floating inputs, missing drivers, power conflicts, missing decoupling, and missing I2C pull-ups over the IR.
*   [x] **Net-label connectivity:** compiled schematics attach a net label at every connected pin (scales to any net size; replaces point-to-point wires).
*   [x] **Footprint assignment:** `backend/services/footprints.py` maps LCSC package strings (0603, SOT-23, SOIC-8, LQFP-48, …) to stock KiCad footprint IDs; explicit `footprint` overrides supported in the IR.
*   [x] **Complete project emission:** `compile_schematic_ir` emits `.kicad_sch` + `.kicad_pro` + generated `.kicad_sym` + project-local `sym-lib-table`, so "Update PCB from Schematic" works directly in KiCad.
*   [x] **Workflow prompt:** the chat system prompt drives architect → source → pinout → connect → verify → compile → fabricate.

### Phase 5: The "PCB Engineer" (Future)
*   [x] **kicad-cli wrapper:** native ERC, netlist/BOM/PDF export, and Gerber/drill export for routed boards (`backend/services/fabrication.py`, `export_fabrication_outputs` tool). Requires KiCad installed server-side; degrades gracefully when absent.
*   [ ] **.kicad_pcb generation:** emit a board file with footprints placed and nets assigned (requires footprint geometry — KiCad footprint libraries server-side or an EasyEDA→KiCad converter for LCSC parts).
*   [ ] **Algorithmic placement:** seed component placement from the block diagram (power entry, MCU-centric clustering, decoupling proximity).
*   [ ] **Autorouting integration:** e.g. freerouting round-trip, or interactive-routing handoff to KiCad.
*   [ ] **Fab package:** one-click JLCPCB bundle (Gerbers, drill, BOM CSV, CPL) once a routed board exists.
