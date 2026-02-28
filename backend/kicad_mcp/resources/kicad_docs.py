"""KiCad reference documentation exposed as MCP resources.

These resources give the agent grounded, version-specific knowledge about
KiCad 9 file formats, symbols, and ERC rules without relying on training data.
"""

from fastmcp import FastMCP


def register_docs(mcp: FastMCP) -> None:
    """Register all KiCad documentation resources with the MCP server.

    Args:
        mcp: The FastMCP server instance to register resources on.
    """

    @mcp.resource("kicad://docs/file-formats")
    def kicad_file_formats() -> str:
        """KiCad 9 file format reference for AI agents."""
        return """# KiCad 9 File Format Reference

## Overview
KiCad uses S-Expression (sexp) based text formats for all design files.
All files are UTF-8 encoded plain text, human-readable and VCS-friendly.

## File Types

### Schematic: `.kicad_sch`
Contains:
- `(kicad_sch (version 20231120) ...)` — root element
- `(lib_symbols ...)` — inline symbol definitions
- `(symbol (lib_id "Device:R") (at X Y angle) (reference "R1") (value "10k") ...)`
- `(wire (pts (xy X1 Y1) (xy X2 Y2)))` — electrical connections
- `(no_connect (at X Y))` — intentional unconnected pin markers
- `(net_tie_pad_groups ...)` — net tie definitions
- `(bus ...)` / `(bus_entry ...)` — bus connections
- `(label (at X Y) (text "NET_NAME"))` — net labels
- `(global_label ...)` — cross-sheet global nets
- `(hierarchical_label ...)` — hierarchical sheet connections
- `(sheet ...)` — sub-sheet references

### PCB Layout: `.kicad_pcb`
Contains:
- `(kicad_pcb (version 20240108) ...)`
- `(setup ...)` — design rules, grid, zones
- `(footprint ...)` — component footprints with pads
- `(segment (start X Y) (end X Y) (layer "F.Cu") (width W) (net N))`
- `(zone ...)` — copper pours / fills
- `(via (at X Y) (size S) (drill D) (layers "F.Cu" "B.Cu") (net N))`

### Project: `.kicad_pro`
JSON format containing:
- Board/schematic settings
- Library table references
- Net inspector settings

### Symbol Library: `.kicad_sym`
- Defines reusable schematic symbols
- Each symbol has pins, graphic primitives, default properties

### Footprint Library: `.kicad_mod`
- Individual component footprints
- Pad definitions, courtyard, fab layers, silkscreen

## Coordinate System
- Units: millimetres (mm) for PCB, mils (1/1000 inch) internally for schematic
- Schematic display coordinates use a Cartesian system where Y increases downward
- Origin (0,0) is top-left for schematics

## Key Rules
- All S-Expressions must be properly nested and closed
- String values with spaces must be quoted: `"My Value"`
- Numbers are floating point: `(at 152.4 114.3)`
- Angles in degrees, counter-clockwise positive
"""

    @mcp.resource("kicad://docs/schematic-symbols")
    def kicad_schematic_symbols() -> str:
        """How KiCad schematic symbols, pins, and nets work."""
        return """# KiCad Schematic Symbols & Connectivity

## Symbol Structure
A placed symbol (component instance) in a schematic:

```sexp
(symbol (lib_id "Device:R") (at 100.0 100.0 0) (unit 1)
  (in_bom yes) (on_board yes)
  (property "Reference" "R1" (at 101.6 98.4 0))
  (property "Value" "10k" (at 101.6 101.6 0))
  (property "Footprint" "Resistor_SMD:R_0402_1005Metric" (at 0 0 0))
  (property "Datasheet" "~" (at 0 0 0))
  (pin "1" (uuid "..."))
  (pin "2" (uuid "..."))
)
```

## Pin Types
- `input` — signal input
- `output` — signal output  
- `bidirectional` — bidirectional (e.g., I2C SDA)
- `tri_state` — tristate output
- `passive` — passive (resistors, capacitors)
- `power_in` — power consumer (VCC pin of IC)
- `power_out` — power provider (power symbol, LDO output)
- `open_collector` / `open_emitter`
- `no_connect` — pin intentionally unused

## Net Labels
- **Local label** `(label)`: connects within one sheet only
- **Global label** `(global_label)`: connects across all sheets in project
- **Hierarchical label** `(hierarchical_label)`: connects to parent/child sheets
- **Power symbol** (e.g., VCC, GND): global net by convention, always `power_out` or `power_in`

## ERC Pin Connectivity Rules
Two pins create a valid connection when:
- They share the same net (connected by wire or label)
- At least one `power_out` or `output` drives the net
- `passive` pins can connect to anything
- `no_connect` marker suppresses ERC warning for unconnected pin

## Reference Designators (Refs)
Standard convention:
- `R` — Resistors
- `C` — Capacitors  
- `L` — Inductors
- `U` — Integrated Circuits
- `Q` — Transistors
- `D` — Diodes
- `J` — Connectors
- `SW` — Switches
- `F` — Fuses
- `Y` / `X` — Crystals/Oscillators
- `TP` — Test Points
- `FB` — Ferrite Beads
"""

    @mcp.resource("kicad://docs/erc-rules")
    def kicad_erc_rules() -> str:
        """KiCad Electrical Rules Check (ERC) explanation and common violations."""
        return """# KiCad ERC Rules Reference

## What is ERC?
Electrical Rules Check validates schematic connectivity for common errors.
It does NOT verify that the circuit will work as intended — it only checks connectivity rules.

## Common ERC Errors

### Pin Conflicts
- **Error:** `Pin unconnected` — A pin has no wire, label, or no-connect marker
- **Fix:** Connect the pin or add a no-connect marker (X symbol)

- **Error:** `Pin not driven` — A net has no driver (output or power_out pin)
- **Fix:** Ensure every net has exactly one driving source

- **Error:** `Multiple drivers` — Two output pins connected together
- **Fix:** Use bus/mux topology, add series resistor, or verify intent

### Power Nets
- **Error:** `Power pin not driven` — A VCC/GND net has no power source
- **Fix:** Add a PWR_FLAG symbol to the net (tells ERC this is intentionally a power rail)

### Bus Issues  
- **Error:** `Bus entry not connected`
- **Error:** `Bus label syntax` — Bus labels must match pattern `NAME[0..N]`

## Common Design Rule Violations (Not ERC but important)

### Decoupling Capacitors
- Every IC VCC pin needs a 100nF ceramic cap within 1mm on PCB
- Bulk decoupling: 10µF electrolytic or MLCC per supply rail
- Place decoupling caps as close as possible to IC power pins

### Pull-up/Pull-down Resistors
- I2C SDA/SCL: 4.7kΩ to VCC (for 100kHz), 2.2kΩ for 400kHz
- RESET pins (active-low): 10kΩ pull-up to VCC
- Unused logic inputs: pull to valid logic level, never float

### ESD Protection
- External connectors should have TVS diodes or ESD protection arrays
- USB data lines: 33Ω series resistors + common-mode choke recommended

## Best Practices Checklist
- [ ] All IC power pins have decoupling caps
- [ ] All unconnected pins have no-connect markers
- [ ] I2C/SPI buses have correct pull-ups
- [ ] Reset/enable pins are driven or pulled
- [ ] PWR_FLAG on all power rails
- [ ] Ferrite bead (FB) between digital and analog VCC where needed
"""
