"""MCP tools for extracting netlist information from KiCad schematics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


def register_netlist_tools(mcp: FastMCP) -> None:
    """Register netlist extraction tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.tool()
    def list_patterns() -> dict[str, Any]:
        """List all available KiCad circuit patterns.

        Returns the name and description of each pattern available in the
        backend knowledge base. Use get_pattern to retrieve full code.

        Returns:
            Dict with key 'patterns' containing list of {name, description} dicts.
        """
        patterns_dir = Path(__file__).parent.parent.parent / "knowledge" / "patterns"
        if not patterns_dir.exists():
            return {"patterns": []}

        patterns = []
        for p in sorted(patterns_dir.glob("*.py")):
            if p.name.startswith("_"):
                continue
            code = p.read_text(encoding="utf-8")
            # Extract description from module docstring
            description = ""
            lines = code.splitlines()
            if lines and lines[0].startswith('"""'):
                end = next((i for i, l in enumerate(lines[1:], 1) if '"""' in l), None)
                if end:
                    description = " ".join(lines[1:end]).strip()
            patterns.append({
                "name": p.stem,
                "description": description or f"Circuit pattern: {p.stem}",
            })

        return {"patterns": patterns}

    @mcp.tool()
    def get_pattern(name: str) -> dict[str, Any]:
        """Retrieve a KiCad circuit pattern by name.

        Patterns are verified, reusable Python code snippets using kicad-sch-api
        to generate common circuit blocks. Use list_patterns to see what's available.

        Args:
            name: Pattern name (e.g. 'ldo_3v3', 'usb_c_upstream', 'mcu_decoupling').

        Returns:
            Dict with keys: name, description, code, error (if not found).
        """
        patterns_dir = Path(__file__).parent.parent.parent / "knowledge" / "patterns"
        path = patterns_dir / f"{name}.py"

        if not path.exists():
            available = [p.stem for p in patterns_dir.glob("*.py") if not p.name.startswith("_")]
            return {
                "error": f"Pattern '{name}' not found.",
                "available_patterns": sorted(available),
            }

        code = path.read_text(encoding="utf-8")
        description = ""
        lines = code.splitlines()
        if lines and lines[0].startswith('"""'):
            end = next((i for i, l in enumerate(lines[1:], 1) if '"""' in l), None)
            if end:
                description = "\n".join(lines[1:end]).strip()

        return {
            "name": name,
            "description": description,
            "code": code,
        }
