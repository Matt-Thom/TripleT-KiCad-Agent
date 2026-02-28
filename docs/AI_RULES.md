# AI Development Rules & Guidelines

## Core Mandates
1.  **Documentation First:** usage of tools, APIs, and architectural decisions must be documented immediately. If you add a feature, update the relevant `docs/*.md` file. **Never leave documentation out of sync with code.**
2.  **KiCad 9 Native:** All file generation and scripting must target **KiCad 9.0+**. Do not rely on deprecated KiCad 6/7/8 patterns unless strictly necessary for compatibility libraries.
3.  **Local-First:** The architecture prioritizes running locally on the user's machine. Cloud calls (AI, Part Search) are the exception, not the rule.

## Coding Standards

### Python (Backend)
*   **Version:** Python 3.12+
*   **Type Hints:** Strict typing required for all function signatures. Use `mypy` to verify.
*   **Style:** Follow `Ruff` defaults (which subsume Black/Isort/Flake8).
*   **Docstrings:** Google Style docstrings for all modules, classes, and public functions.
*   **Testing:** `pytest` is the standard. All new endpoints/logic must have accompanying tests.

### TypeScript (Frontend)
*   **Framework:** React + Tailwind CSS.
*   **Strict Mode:** Enabled. No `any` types unless absolutely unavoidable.
*   **Components:** Functional components with Hooks.

### Version Control
*   **Commits:** Follow Conventional Commits specification.
    *   `feat: ...` for new features.
    *   `fix: ...` for bug fixes.
    *   `docs: ...` for documentation updates.
    *   `chore: ...` for maintenance.
*   **Branches:**
    *   `main`: Stable release.
    *   `dev`: Integration branch.
    *   `feature/*`: Individual feature branches.

## Architectural Patterns
*   **RAG over Fine-tuning:** Use Retrieval-Augmented Generation for specialized knowledge.
    *   **The Cookbook:** All schematic generation logic must rely on verified snippets from `backend/knowledge/patterns/`.
    *   **Fact Checking:** The AI must use the `datasheet_reader` tool (when available) to verify pinouts and values against manufacturer specs.
*   **Unified Part Model:** All part data (from LCSC, DigiKey, etc.) must be normalized to the internal `Part` schema before being used by the application.

## Knowledge Management
*   **Pattern Storage:** Common circuit designs (e.g., USB-C input) must be saved as Python scripts in `backend/knowledge/patterns/`.
*   **No Hallucinations:** If a pattern does not exist, the Agent must either:
    1.  Search for a similar verified pattern.
    2.  Explicitly state it is generating a "Best Effort" design and request user verification.

## KiCad MCP Server

The project ships a local MCP (Model Context Protocol) server at `backend/kicad_mcp/`. All AI agents working on this project **must** use it as the primary source of KiCad knowledge rather than relying on training data.

### When to Use the MCP Server
*   **Always** use `parse_schematic` before analysing or modifying a `.kicad_sch` file.
*   **Always** use `validate_schematic` after generating or editing a schematic.
*   **Always** call `list_patterns` + `get_pattern` before writing new schematic generation code — use an existing verified pattern if one exists.
*   Use `extract_bom` when the user asks about components, quantities, or BOM export.
*   Use `generate_schematic_stub` as the starting point for new schematics, not a blank file.

### MCP Resources (inject into context before answering KiCad questions)
*   `kicad://docs/file-formats` — KiCad 9 S-Expression format reference
*   `kicad://docs/schematic-symbols` — pin types, net labels, ERC connectivity
*   `kicad://docs/erc-rules` — ERC rules and common design violations
*   `kicad://patterns/list` — index of all available circuit patterns

### Adding New Patterns
When a new verified circuit block is created:
1.  Save it as `backend/knowledge/patterns/<name>.py`
2.  Start the file with a Google-style module docstring describing the circuit
3.  Include LCSC part numbers, component values, and layout notes
4.  Register it with a test in `backend/tests/test_kicad_mcp.py`

### Running the MCP Server
```bash
# stdio (Claude Desktop)
python -m backend.kicad_mcp.server

# HTTP/SSE (FastAPI mount — see backend/main.py)
# Mounted at /mcp automatically when the backend starts
```

See `docs/KICAD_MCP_SPEC.md` for the full specification.
