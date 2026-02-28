"""3.3V LDO Regulator with input/output decoupling capacitors.

Implements a standard AMS1117-3.3 (or compatible MCP1700) LDO:
- Input: 4.5–12V
- Output: 3.3V @ up to 800mA
- Input cap: 10µF electrolytic + 100nF MLCC
- Output cap: 10µF electrolytic + 100nF MLCC
- Optional: LED power indicator with 1kΩ series resistor

Footprints target LCSC Basic Parts where possible.
"""

# kicad-sch-api generation script for AMS1117-3.3 LDO
# Requires: pip install kicad-sch-api

COMPONENTS = [
    # U1: AMS1117-3.3  SOT-223  LCSC: C6186
    {"ref": "U1", "value": "AMS1117-3.3", "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2"},
    # C1: 10µF input bulk cap  0805  LCSC: C19702
    {"ref": "C1", "value": "10uF", "footprint": "Capacitor_SMD:C_0805_2012Metric"},
    # C2: 100nF input decoupling  0402  LCSC: C14663
    {"ref": "C2", "value": "100nF", "footprint": "Capacitor_SMD:C_0402_1005Metric"},
    # C3: 10µF output bulk cap  0805  LCSC: C19702
    {"ref": "C3", "value": "10uF", "footprint": "Capacitor_SMD:C_0805_2012Metric"},
    # C4: 100nF output decoupling  0402  LCSC: C14663
    {"ref": "C4", "value": "100nF", "footprint": "Capacitor_SMD:C_0402_1005Metric"},
]

NETS = {
    "VIN": "Input voltage net (4.5–12V)",
    "+3V3": "Regulated 3.3V output net",
    "GND": "Ground",
}

NOTES = """
AMS1117-3.3 Pin Map (SOT-223):
  Pin 1 — GND (Adjust / ground)
  Pin 2 (Tab) — Output (+3V3)
  Pin 3 — Input (VIN)

Place C1+C2 within 2mm of U1 input pin on PCB.
Place C3+C4 within 2mm of U1 output tab on PCB.
Tab pin must be connected to +3V3 net and have thermal vias for heat dissipation.
Max power dissipation: (VIN - 3.3) × ILOAD. Derate if VIN > 7V at high current.
"""

EXAMPLE_CODE = '''
# Example using kicad-sch-api (pseudocode — adapt to actual API version)
from kicad_sch_api import Schematic, Symbol, Wire, Net

sch = Schematic()

# Place LDO
u1 = sch.add_symbol("AMS1117-3.3", ref="U1", at=(100, 100))

# Place decoupling caps
c1 = sch.add_symbol("C", ref="C1", value="10uF", at=(80, 90))
c2 = sch.add_symbol("C", ref="C2", value="100nF", at=(80, 100))
c3 = sch.add_symbol("C", ref="C3", value="10uF", at=(120, 90))
c4 = sch.add_symbol("C", ref="C4", value="100nF", at=(120, 100))

# Connect nets
sch.add_power_symbol("VIN", at=(80, 80))
sch.add_power_symbol("+3V3", at=(120, 80))
sch.add_power_symbol("GND", at=(100, 120))

sch.save("ldo_3v3_output.kicad_sch")
'''
