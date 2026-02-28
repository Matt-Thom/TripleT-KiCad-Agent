"""Circuit pattern resources for MCP.

Exposes the backend/knowledge/patterns/ directory as MCP resources,
allowing agents to retrieve curated, verified schematic code snippets.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

PATTERNS_DIR = Path(__file__).parent.parent.parent / "knowledge" / "patterns"


def _load_pattern_meta(path: Path) -> dict:
    """Load pattern metadata from a .py file's docstring.

    Args:
        path: Path to the pattern Python file.

    Returns:
        Dict with name, description, and code keys.
    """
    code = path.read_text(encoding="utf-8")
    # Extract description from module docstring (first triple-quoted string)
    description = ""
    lines = code.splitlines()
    if lines and lines[0].startswith('"""'):
        end = next((i for i, l in enumerate(lines[1:], 1) if '"""' in l), None)
        if end:
            description = "\n".join(lines[1:end]).strip()
    return {
        "name": path.stem,
        "description": description or f"Circuit pattern: {path.stem}",
        "code": code,
    }


def register_patterns(mcp: FastMCP) -> None:
    """Register circuit pattern resources with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.resource("kicad://patterns/list")
    def list_patterns_resource() -> str:
        """Index of all available KiCad circuit patterns."""
        if not PATTERNS_DIR.exists():
            return json.dumps({"patterns": []})
        patterns = []
        for p in sorted(PATTERNS_DIR.glob("*.py")):
            if p.name.startswith("_"):
                continue
            meta = _load_pattern_meta(p)
            patterns.append({"name": meta["name"], "description": meta["description"]})
        return json.dumps({"patterns": patterns}, indent=2)

    @mcp.resource("kicad://patterns/{name}")
    def get_pattern_resource(name: str) -> str:
        """Retrieve a specific circuit pattern by name.

        Args:
            name: Pattern file stem (e.g. 'ldo_3v3').
        """
        path = PATTERNS_DIR / f"{name}.py"
        if not path.exists():
            return json.dumps({"error": f"Pattern '{name}' not found"})
        meta = _load_pattern_meta(path)
        return json.dumps(meta, indent=2)
