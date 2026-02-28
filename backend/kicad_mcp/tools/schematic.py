"""MCP tools for parsing, validating, and generating KiCad schematics.

Targets KiCad 9.0 S-Expression format. All file I/O is read-only except
for generate_schematic_stub which writes to a user-specified output path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_sexp(file_path: str) -> str:
    """Read and return raw S-Expression content from a KiCad file.

    Args:
        file_path: Absolute or relative path to the .kicad_sch file.

    Returns:
        Raw file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file does not appear to be a KiCad schematic.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    content = path.read_text(encoding="utf-8")
    if "(kicad_sch" not in content:
        raise ValueError(f"File does not appear to be a KiCad schematic: {file_path}")
    return content


def _extract_symbols(content: str) -> list[dict[str, str]]:
    """Extract placed symbol instances from schematic content.

    Args:
        content: Raw schematic S-Expression content.

    Returns:
        List of dicts with ref, value, lib_id, and footprint keys.
    """
    components: list[dict[str, str]] = []
    # Match top-level symbol blocks (not inside lib_symbols)
    # Look for (symbol (lib_id "...") ... (property "Reference" "Rx" ...) ...)
    symbol_blocks = re.findall(
        r'\(symbol\s+\(lib_id\s+"([^"]+)"\)(.*?)\(pin\s+"\d+"\s+\(uuid',
        content,
        re.DOTALL,
    )
    for lib_id, body in symbol_blocks:
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', body)
        val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', body)
        fp_match = re.search(r'\(property\s+"Footprint"\s+"([^"]+)"', body)
        components.append(
            {
                "ref": ref_match.group(1) if ref_match else "?",
                "value": val_match.group(1) if val_match else "?",
                "lib_id": lib_id,
                "footprint": fp_match.group(1) if fp_match else "",
            }
        )
    return components


def _extract_nets(content: str) -> list[str]:
    """Extract unique net names from label and global_label elements.

    Args:
        content: Raw schematic S-Expression content.

    Returns:
        Sorted list of unique net names found in the schematic.
    """
    nets: set[str] = set()
    # Local labels
    for m in re.finditer(r'\(label\s+\(text\s+"([^"]+)"\)', content):
        nets.add(m.group(1))
    # Global labels
    for m in re.finditer(r'\(global_label\s+\(text\s+"([^"]+)"\)', content):
        nets.add(m.group(1))
    # Net ties / power symbols (property "Value" on power symbols)
    for m in re.finditer(r'\(lib_id\s+"power:([^"]+)"\)', content):
        nets.add(m.group(1))
    return sorted(nets)


def _count_wires(content: str) -> int:
    """Count the number of wire segments in the schematic.

    Args:
        content: Raw schematic S-Expression content.

    Returns:
        Number of wire segments.
    """
    return len(re.findall(r'\(wire\s+\(pts', content))


def _count_no_connects(content: str) -> int:
    """Count no-connect markers in the schematic.

    Args:
        content: Raw schematic S-Expression content.

    Returns:
        Number of no-connect markers.
    """
    return len(re.findall(r'\(no_connect\s+\(at', content))


def _find_power_symbols(content: str) -> list[str]:
    """Extract power symbol names used in the schematic.

    Args:
        content: Raw schematic S-Expression content.

    Returns:
        Sorted list of unique power symbol names (e.g. ['GND', 'VCC', '+3V3']).
    """
    power_syms: set[str] = set()
    for m in re.finditer(r'\(lib_id\s+"power:([^"]+)"\)', content):
        power_syms.add(m.group(1))
    return sorted(power_syms)


def _basic_erc_checks(
    components: list[dict[str, str]],
    nets: list[str],
    wire_count: int,
    no_connect_count: int,
    content: str,
) -> dict[str, list[str]]:
    """Run basic ERC-style heuristic checks on parsed schematic data.

    Args:
        components: Parsed component list.
        nets: Extracted net names.
        wire_count: Number of wire segments.
        no_connect_count: Number of no-connect markers.
        content: Raw schematic content for additional pattern matching.

    Returns:
        Dict with 'errors', 'warnings', and 'info' lists.
    """
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    if wire_count == 0 and components:
        errors.append("Schematic has components but no wire segments — connectivity is missing.")

    # Check for PWR_FLAG on power nets (absence is a common ERC error)
    if "PWR_FLAG" not in content and any(
        n in nets for n in ["VCC", "VDD", "+3V3", "+5V", "+12V"]
    ):
        warnings.append(
            "No PWR_FLAG symbol detected. KiCad ERC will warn about undriven power nets. "
            "Add a PWR_FLAG to each power rail."
        )

    # Heuristic: check for decoupling caps near ICs
    ic_refs = [c for c in components if c["ref"].startswith("U")]
    cap_count = sum(1 for c in components if c["ref"].startswith("C"))
    if ic_refs and cap_count == 0:
        warnings.append(
            f"{len(ic_refs)} IC(s) found but no capacitors. "
            "Add 100nF decoupling caps on each VCC pin."
        )
    elif ic_refs and cap_count < len(ic_refs):
        warnings.append(
            f"{len(ic_refs)} IC(s) but only {cap_count} capacitor(s). "
            "Ensure each IC VCC pin has at least one 100nF decoupling cap."
        )
    elif ic_refs and cap_count >= len(ic_refs):
        info.append(f"{cap_count} decoupling capacitor(s) found for {len(ic_refs)} IC(s).")

    if no_connect_count > 0:
        info.append(f"{no_connect_count} no-connect marker(s) present.")

    # Check for reset pins without pull-ups (heuristic)
    if any("reset" in c["lib_id"].lower() or "nrst" in c["value"].lower() for c in components):
        info.append(
            "Component(s) with RESET pins detected. "
            "Verify NRST/RESET is pulled up with 10kΩ to VCC."
        )

    return {"errors": errors, "warnings": warnings, "info": info}


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_schematic_tools(mcp: FastMCP) -> None:
    """Register all schematic-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.tool()
    def parse_schematic(file_path: str) -> dict[str, Any]:
        """Parse a KiCad 9 schematic file and return a structured summary.

        Extracts components, nets, wire count, power symbols, and basic stats.
        Use this before calling validate_schematic or extract_bom.

        Args:
            file_path: Absolute path to a .kicad_sch file.

        Returns:
            Dict with keys: components, nets, wire_count, no_connect_count,
            power_symbols, component_count, error (if any).
        """
        try:
            content = _read_sexp(file_path)
        except (FileNotFoundError, ValueError) as exc:
            return {"error": str(exc)}

        components = _extract_symbols(content)
        nets = _extract_nets(content)
        wire_count = _count_wires(content)
        no_connect_count = _count_no_connects(content)
        power_symbols = _find_power_symbols(content)

        return {
            "components": components,
            "component_count": len(components),
            "nets": nets,
            "wire_count": wire_count,
            "no_connect_count": no_connect_count,
            "power_symbols": power_symbols,
        }

    @mcp.tool()
    def validate_schematic(file_path: str) -> dict[str, Any]:
        """Run basic ERC-style validation checks on a KiCad schematic.

        Checks include: missing decoupling caps, absent PWR_FLAG symbols,
        zero wire count, and common omissions. Does not replace KiCad's
        built-in ERC — use this for a quick AI-assisted sanity check.

        Args:
            file_path: Absolute path to a .kicad_sch file.

        Returns:
            Dict with keys: errors (list), warnings (list), info (list),
            and error (str) if the file could not be read.
        """
        try:
            content = _read_sexp(file_path)
        except (FileNotFoundError, ValueError) as exc:
            return {"error": str(exc)}

        components = _extract_symbols(content)
        nets = _extract_nets(content)
        wire_count = _count_wires(content)
        no_connect_count = _count_no_connects(content)

        return _basic_erc_checks(components, nets, wire_count, no_connect_count, content)

    @mcp.tool()
    def extract_bom(file_path: str) -> dict[str, Any]:
        """Extract a Bill of Materials from a KiCad schematic.

        Returns all component instances with their reference designator, value,
        footprint, and lib_id. Components sharing the same value+footprint are
        grouped for BOM consolidation.

        Args:
            file_path: Absolute path to a .kicad_sch file.

        Returns:
            Dict with keys: components (list), total_components (int),
            total_unique_parts (int), grouped_bom (list), error (str if any).
        """
        try:
            content = _read_sexp(file_path)
        except (FileNotFoundError, ValueError) as exc:
            return {"error": str(exc)}

        components = _extract_symbols(content)

        # Group by value + footprint
        groups: dict[str, dict[str, Any]] = {}
        for comp in components:
            key = f"{comp['value']}|{comp['footprint']}"
            if key not in groups:
                groups[key] = {
                    "value": comp["value"],
                    "footprint": comp["footprint"],
                    "lib_id": comp["lib_id"],
                    "refs": [],
                    "quantity": 0,
                }
            groups[key]["refs"].append(comp["ref"])
            groups[key]["quantity"] += 1

        grouped_bom = sorted(groups.values(), key=lambda x: x["quantity"], reverse=True)

        return {
            "components": components,
            "total_components": len(components),
            "total_unique_parts": len(groups),
            "grouped_bom": grouped_bom,
        }

    @mcp.tool()
    def generate_schematic_stub(description: str, output_path: str) -> dict[str, Any]:
        """Generate a minimal KiCad 9 schematic stub file.

        Creates a blank-but-valid .kicad_sch file with a title block populated
        from the description. This gives the user a starting point to open in
        KiCad and populate. For full schematic generation, use the kicad-sch-api
        patterns in backend/knowledge/patterns/.

        Args:
            description: Natural language description of the circuit (used as title).
            output_path: Absolute path where the .kicad_sch file will be written.

        Returns:
            Dict with keys: success (bool), file_path (str), notes (str),
            error (str if any).
        """
        # Sanitise description for use in sexp (escape quotes)
        safe_desc = description.replace('"', "'")
        stub = f"""(kicad_sch
  (version 20231120)
  (generator "TripleT-KiCad-Agent")
  (generator_version "0.1")
  (paper "A4")
  (title_block
    (title "{safe_desc}")
    (comment 1 "Generated by TripleT KiCad Agent — verify all values before use")
  )
  (lib_symbols)
  (no_connects)
  (wire)
  (sheets)
  (symbols)
  (buses)
  (net_tie_pad_groups)
  (global_labels)
  (hierarchical_labels)
  (images)
  (polylines)
  (rectangles)
  (circles)
  (arcs)
  (texts)
  (text_boxes)
  (bitmaps)
)
"""
        try:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(stub, encoding="utf-8")
        except OSError as exc:
            return {"success": False, "error": str(exc)}

        return {
            "success": True,
            "file_path": str(out.resolve()),
            "notes": (
                "Minimal stub generated. Open in KiCad 9 and add components. "
                "For a populated schematic, use generate_schematic_stub with a circuit "
                "pattern from list_patterns."
            ),
        }
