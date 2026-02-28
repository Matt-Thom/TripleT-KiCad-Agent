"""TripleT KiCad MCP Server.

Exposes KiCad knowledge and file-operation tools via the Model Context Protocol,
allowing any MCP-compatible AI agent (Claude Desktop, Cursor, etc.) to understand
KiCad 9 schematics, validate designs, and access curated circuit patterns.

Usage (stdio, for Claude Desktop):
    uv run python -m backend.kicad_mcp.server

Usage (HTTP/SSE, for FastAPI integration):
    from backend.kicad_mcp.server import mcp
    app.mount("/mcp", mcp.get_asgi_app())
"""

import sys

from fastmcp import FastMCP

from backend.kicad_mcp.resources.kicad_docs import register_docs
from backend.kicad_mcp.resources.patterns import register_patterns
from backend.kicad_mcp.tools.schematic import register_schematic_tools
from backend.kicad_mcp.tools.netlist import register_netlist_tools
from backend.kicad_mcp.prompts.design_review import register_prompts

mcp = FastMCP(
    name="kicad",
    instructions=(
        "You are a KiCad 9 expert assistant. Use the provided tools to parse, "
        "validate, and generate KiCad schematics. Always verify component values "
        "against datasheets and flag any 'Best Effort' designs that need user review."
    ),
)

# Register all resources, tools, and prompts
register_docs(mcp)
register_patterns(mcp)
register_schematic_tools(mcp)
register_netlist_tools(mcp)
register_prompts(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
