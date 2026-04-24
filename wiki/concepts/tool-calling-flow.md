---
title: Tool-Calling Flow
type: concept
tags: [ai, tools, agent, litellm]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/services/ai.py, backend/services/tools.py, backend/main.py]
---

How one `POST /api/chat` request walks the tool graph.

## Tools available

| Tool | Purpose | Typical callers |
|---|---|---|
| `search_lcsc` | Part search. One component per call. | First step for any sourcing question. |
| `lookup_pattern` | BM25 over the pattern library. | Before `apply_pattern`, always. |
| `apply_pattern` | Runs a verified sub-circuit pattern. | LDO, USB-C input, I²C pull-ups, MCU reset. |
| `extract_pinout` | Datasheet URL → validated `PinSpec[]` via a dedicated LLM call. | Before `generate_schematic` when a real multi-pin symbol is wanted. |
| `generate_schematic` | Emits a `.kicad_sch`. Accepts optional `pins` array. | Final step for single-component schematics. |

Full schemas: `backend/services/tools.py`. Dispatcher: `execute_tool()` in the same file.

## Canonical chains

### Simple part source

```
user: "find me a 0603 10k resistor"
  → search_lcsc(query="0603 10k resistor")
  → [final answer]
```

### Standard sub-circuit

```
user: "give me a 3.3V LDO from a 5V input"
  → lookup_pattern(query="3.3V LDO 5V input")
  → apply_pattern(pattern_id="ldo_regulator", inputs={vin:5, vout:3.3})
  → [download link]
```

### Custom IC with real pinout

```
user: "make a schematic for the STM32F103C8T6"
  → search_lcsc(query="STM32F103C8T6")      // get supplier_id + maybe datasheet_url
  → extract_pinout(datasheet_url, mpn)       // real multi-pin PinSpec[]
  → generate_schematic(mpn, supplier_id, pins=[...])
  → [download link]
```

## Loop mechanics

See [[entities/ai-service]] for the full invariants. Key points:

- The loop is **synchronous** from the agent's point of view — each tool call completes before the next LiteLLM round-trip.
- Tool results are always converted to strings. Structured results (`search_lcsc`, `extract_pinout`) are serialized as `repr()` or `json.dumps` so the model can parse them back.
- Errors in tools don't crash the loop. They become strings the model sees and can reason about.
- `AI_MAX_TOOL_TURNS` (default 6) caps the chain length. Hitting it returns a fixed "try smaller steps" reply — the model does not get to produce a normal final answer.

## Designing a new tool

1. Add an entry to `tools = [...]` in `backend/services/tools.py` with a clear `name`, `description` (the model reads this), and a strict JSON schema for `parameters`.
2. Add a branch to `execute_tool()` that returns **a string** (stringify any structured result).
3. If the tool should be used by default for certain requests, update the system prompt in `backend/main.py:127` to nudge the model toward it.
4. Write tests in `backend/tests/test_<tool>.py` following [[concepts/testing-strategy]].

## Related

- [[entities/ai-service]]
- [[entities/pinout-extractor]] — exemplar of a "tool that is itself an LLM call".
