# TripleT KiCad Agent - Project Plan

## Overview
The TripleT KiCad Agent is an AI-powered engineering assistant designed to bridge the gap between high-level system requirements and physical PCB design.

## Status
**Phase:** MVP Complete (Search, Chat, Basic Generation)

## Next Phase: The "Schematic Drafter" (Real Symbols)

### 1. Advanced Symbol Generation
*   **Problem:** Currently, generated schematics use a placeholder "Box with Pin 1" because we lack pinout data.
*   **Solution:** Implement a **Pinout Extraction** workflow.
    *   **Data Source:** Use the AI (Gemini 3/GPT-5) to read the Datasheet URL (found via LCSC Search).
    *   **Extraction:** The AI extracts the Pin Table (Pin Number, Name, Type) into a JSON format.
    *   **Generation:** Update `SchematicService` to accept this JSON and draw a rectangle with the correct number of pins, names, and electrical types (Input, Output, Power).

### 2. KiCad Library Integration
*   **Goal:** Use the user's *actual* installed symbols if available.
*   **Mechanism:**
    *   Parse the user's `sym-lib-table` (path provided in Settings).
    *   Search local libraries before generating a custom symbol.

### 3. Multi-Part Schematics
*   **Goal:** "Connect an STM32 to a Sensor."
*   **Mechanism:**
    *   Generate symbols for both parts.
    *   Place them on the sheet (algorithmic layout).
    *   Draw wires between matching nets (e.g., SDA -> SDA, SCL -> SCL).

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

### Phase 3: The "Symbol Engineer" [COMPLETED]
*   [x] **Datasheet Reading:** `backend/services/datasheet.py` fetches PDFs via `httpx` and extracts text with `pdfplumber`.
*   [x] **Pinout Extractor:** `extract_pinout` AI tool runs a dedicated LLM call to turn datasheet text into a validated `PinSpec[]`. Drops pins with unknown electrical types, raises on malformed output.
*   [x] **Procedural Symbol Generator:** Python code to draw complex symbols from Pin Lists.
*   [x] **Library Reuse:** Schematic generator prefers existing symbols from the user's `sym-lib-table`; falls back to the procedural generator only when no library hit is found.
*   [x] **Chain to generate_schematic:** `generate_schematic` accepts an optional `pins` array so the agent can wire `search_lcsc` → `extract_pinout` → `generate_schematic(..., pins=...)`.

### Phase 4: The "Circuit Designer" (Future)
*   [ ] Algorithmic placement of components.
*   [ ] Automatic wiring of standard interfaces (I2C, SPI, UART).
