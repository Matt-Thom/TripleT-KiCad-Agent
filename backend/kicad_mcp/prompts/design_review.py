"""MCP Prompt templates for KiCad design review workflows."""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register design workflow prompt templates with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.prompt()
    def design_review(schematic_path: str) -> str:
        """Multi-step design review workflow for a KiCad schematic.

        Args:
            schematic_path: Path to the .kicad_sch file to review.
        """
        return f"""Please perform a thorough design review of the KiCad schematic at:
{schematic_path}

Follow these steps in order:

1. **Parse the schematic** — Use the `parse_schematic` tool to get a structured overview:
   - How many components are there?
   - What nets and power rails are present?
   - Are there any obvious missing elements?

2. **Run ERC validation** — Use the `validate_schematic` tool:
   - List all errors (must fix)
   - List all warnings (should review)
   - Acknowledge informational items

3. **Extract the BOM** — Use the `extract_bom` tool:
   - How many unique part types are there?
   - Are reference designators sequential and consistent?
   - Flag any components with missing footprints

4. **Cross-check against patterns** — Use `list_patterns` and `get_pattern` to:
   - Identify which circuit blocks are present (power supply, MCU, comms, etc.)
   - Compare implementation against the known-good pattern for each block
   - Note any deviations from best practice

5. **Summarise findings** with:
   - 🔴 Critical issues (will cause failure)
   - 🟡 Warnings (should be addressed)
   - 🟢 Looks good (confirmed correct)
   - 💡 Suggestions (optional improvements)
"""

    @mcp.prompt()
    def part_selection(requirement: str) -> str:
        """Guide the agent through requirement → component → schematic workflow.

        Args:
            requirement: Natural language description of what the circuit must do.
        """
        return f"""You need to select components and design a circuit for this requirement:

"{requirement}"

Follow this structured approach:

1. **Break down the requirement** into functional blocks:
   - What are the key electrical functions needed?
   - What are the voltage, current, and interface requirements?
   - What are the size, cost, or availability constraints?

2. **Identify candidate components** for each block:
   - Use the `search_lcsc` API endpoint to find real, in-stock parts
   - Prioritise LCSC Basic Parts (lower cost, better availability)
   - Check datasheet for key parameters match requirements

3. **Check for matching patterns** using `list_patterns`:
   - Does a verified circuit pattern exist for any of these blocks?
   - If yes, retrieve it with `get_pattern` and adapt to the selected components
   - If no pattern exists, flag this as a "Best Effort" design requiring verification

4. **Generate a schematic stub** using `generate_schematic_stub`:
   - Create the output file
   - Document which pattern(s) were used
   - List components that need to be placed

5. **Final checklist before delivery:**
   - [ ] All power rails have decoupling
   - [ ] All ICs have their enable/reset pins handled
   - [ ] Interface levels match (3.3V vs 5V logic)
   - [ ] ESD protection on external connectors
   - [ ] Current capacity of power supply covers total load + 30% margin
"""
