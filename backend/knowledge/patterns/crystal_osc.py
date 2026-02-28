"""Crystal Oscillator with load capacitors for MCU clock input.

Standard parallel-resonant crystal circuit for MCU HSE (High Speed External) clock.

Load capacitor calculation:
  CL_total = (C1 × C2) / (C1 + C2) + C_stray
  For matched caps: CL_total = C/2 + C_stray
  C_stray ≈ 3–5pF (PCB traces + MCU pin capacitance)
  
  If crystal specifies CL = 12pF and C_stray = 5pF:
  C_ext = 2 × (CL - C_stray) = 2 × (12 - 5) = 14pF → use 15pF standard value

Common crystal frequencies:
- 8 MHz — STM32 common, many options
- 12 MHz — USB-friendly (divide to 48MHz)
- 16 MHz — Arduino/AVR standard
- 25 MHz — Ethernet PHY reference
- 32.768 kHz — RTC (separate circuit, use dedicated XTAL pins)
"""

COMPONENTS = {
    "standard": [
        {"ref": "Y1", "value": "8MHz", "footprint": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
         "note": "8MHz crystal, 12pF load, ±20ppm. LCSC: C115962. Adjust value and CL to design."},
        {"ref": "C7", "value": "15pF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
         "note": "Crystal load cap (matched pair). LCSC: C1634. Calculate per crystal CL spec."},
        {"ref": "C8", "value": "15pF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
         "note": "Crystal load cap (matched pair). LCSC: C1634."},
        {"ref": "R5", "value": "0R", "footprint": "Resistor_SMD:R_0402_1005Metric",
         "note": "Optional series resistor for oscillation stability. DNP unless needed."},
    ]
}

LAYOUT_RULES = """
Critical PCB layout rules for crystal circuits:
1. Place crystal as close as possible to MCU OSC_IN/OSC_OUT pins (< 5mm)
2. Load caps connect from each crystal pin to GND, NOT to each other
3. Use a GND pour under the crystal — tie crystal case to GND if possible
4. Keep crystal traces SHORT, MATCHED in length, and away from other signals
5. Do NOT route high-speed signals under or near the crystal
6. Crystal traces must not cross split planes
7. Series resistor (R5) is usually 0Ω DNP — only install if MCU datasheet requires
   or if oscillation is unstable (check with oscilloscope)
"""

NOTES = """
If the MCU has internal RC oscillator, consider using it for non-timing-critical
applications to save BOM cost and PCB space.

For USB applications requiring precise clock:
- 12MHz crystal allows clean PLL multiplication to 48MHz
- Alternatively use a USB-specific crystal (e.g. 48MHz direct if supported)

RTC crystal (32.768kHz) is a separate circuit — use MCU's dedicated LSE pins,
smaller 2012 footprint crystal (e.g. ABS06-32.768kHz), and 6–12pF load caps.
"""
