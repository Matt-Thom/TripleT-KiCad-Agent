# KiCad MCP — Specification

## Overview

Add a **Model Context Protocol (MCP) server** to the TripleT KiCad Agent that exposes structured KiCad knowledge and live workspace tools to any MCP-compatible AI agent (Claude, Cursor, Copilot, etc.).

The MCP server acts as a domain-specific knowledge and tooling layer — it replaces ad-hoc prompting with reliable, schema-validated tool calls the agent can always depend on.

---

## Motivation

The agent currently relies on:
- Hardcoded prompts for KiCad knowledge
- Manual RAG lookups from `backend/knowledge/patterns/`
- No live access to KiCad workspace state

This means the agent must "know" KiCad from its training data — which is imprecise, version-lagged, and prone to hallucination. An MCP server fixes this by giving the agent **callable tools** backed by real data.

---

## Goals

1. Expose KiCad knowledge as structured MCP **resources** (static reference data)
2. Expose KiCad capabilities as MCP **tools** (callable actions)
3. Support KiCad 9.0 file formats (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`)
4. Run locally alongside the existing FastAPI backend
5. Be consumable by Claude Desktop, Cursor, and any MCP-compatible client

---

## Architecture

```
┌─────────────────────────────────┐
│      AI Agent / Claude          │
└────────────┬────────────────────┘
             │ MCP (stdio or HTTP/SSE)
┌────────────▼────────────────────┐
│      kicad_mcp/server.py        │  ← MCP Server (FastMCP)
│                                 │
│  Resources:  knowledge/         │  ← Static KiCad docs & patterns
│  Tools:      file parsers       │  ← Parse .kicad_sch / .kicad_pcb
│              validators         │  ← Validate netlist, DRC rules
│              generators         │  ← Create schematic stubs
└─────────────────────────────────┘
```

The MCP server lives at `backend/kicad_mcp/` and can be launched as:
- **stdio transport** — for Claude Desktop / local agent integration
- **HTTP/SSE transport** — for the existing FastAPI backend to proxy through

---

## Directory Structure

```
backend/
  kicad_mcp/
    __init__.py
    server.py          ← MCP server entry point (FastMCP)
    resources/
      __init__.py
      kicad_docs.py    ← KiCad file format reference docs as MCP resources
      patterns.py      ← Curated circuit pattern snippets as resources
    tools/
      __init__.py
      schematic.py     ← Parse, validate, generate .kicad_sch files
      pcb.py           ← Parse .kicad_pcb files (Phase 2)
      netlist.py       ← Extract netlist info from schematics
    prompts/
      __init__.py
      design_review.py ← Prompt templates for design review workflows
```

---

## MCP Resources

Resources are static/cached reference data injected into agent context.

| Resource URI | Description |
|---|---|
| `kicad://docs/file-formats` | KiCad 9 S-Expression file format reference |
| `kicad://docs/schematic-symbols` | How schematic symbols, pins, and nets work |
| `kicad://docs/erc-rules` | Electrical Rules Check (ERC) explanation |
| `kicad://patterns/list` | Index of available circuit patterns |
| `kicad://patterns/{name}` | Individual pattern file (Python + description) |

---

## MCP Tools

### `parse_schematic`
Parse a `.kicad_sch` file and return a structured summary.

**Input:** `{ "file_path": "/path/to/project.kicad_sch" }`

**Output:** components list, nets, wire count, power symbols

---

### `validate_schematic`
Run basic ERC-style checks: unconnected pins, missing decoupling, floating nets.

**Input:** `{ "file_path": "/path/to/project.kicad_sch" }`

**Output:** errors, warnings, info messages

---

### `get_pattern`
Retrieve a named circuit pattern (code + description).

**Input:** `{ "name": "usb_c_pd_input" }`

---

### `list_patterns`
List all available circuit patterns with descriptions.

---

### `generate_schematic_stub`
Generate a minimal `.kicad_sch` stub from a natural language description.

**Input:** `{ "description": "5V LDO regulator", "output_path": "/tmp/ldo.kicad_sch" }`

---

### `extract_bom`
Extract a Bill of Materials from a schematic file.

**Input:** `{ "file_path": "/path/to/project.kicad_sch" }`

---

## MCP Prompts

| Prompt | Description |
|---|---|
| `design_review` | Walk through ERC + BOM review of a schematic |
| `part_selection` | Guide from requirement → component search → placement |

---

## Transport & Integration

### Claude Desktop (stdio)
```json
{
  "mcpServers": {
    "kicad": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.kicad_mcp.server"],
      "cwd": "/path/to/TripleT-KiCad-Agent"
    }
  }
}
```

### FastAPI Integration
```python
from backend.kicad_mcp.server import mcp
app.mount("/mcp", mcp.get_asgi_app())
```

---

## Dependencies

Add to project: `fastmcp>=2.0`

---

## Initial Patterns (Seed Data)

1. `ldo_3v3.py` — AMS1117/MCP1700 LDO with decoupling
2. `mcu_decoupling.py` — Per-pin VCC decoupling for STM32/RP2040
3. `usb_c_upstream.py` — USB-C upstream port with CC pull-downs (5.1kΩ)
4. `crystal_osc.py` — Crystal oscillator with load capacitors
5. `i2c_pullup.py` — I2C bus with pull-up calculation

---

## Testing

- `backend/tests/test_kicad_mcp.py` — Unit tests for all MCP tools
- Fixture `.kicad_sch` files in `backend/tests/fixtures/`

---

## Out of Scope (This Phase)

- Live KiCad IPC integration (Phase 3)
- PCB file parsing (Phase 2)
- Footprint library querying

---

## Success Criteria

- [ ] `fastmcp` server starts via stdio and HTTP
- [ ] All 5 tools respond correctly to valid inputs
- [ ] 3+ seed patterns available
- [ ] Parse tool handles a real `.kicad_sch` file
- [ ] Tests pass with `pytest`
- [ ] Claude Desktop can connect and list tools
