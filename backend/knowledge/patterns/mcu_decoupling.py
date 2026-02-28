"""MCU Power Decoupling — best practice for STM32 / RP2040 class microcontrollers.

Every VCC/VDDA/VDDIO pin on an MCU requires its own 100nF decoupling capacitor
placed as close as possible to the pin. A shared bulk capacitor (10µF) is placed
once per supply rail.

This pattern covers:
- Per-pin 100nF X5R/X7R MLCC (0402) on each power pin
- 4.7µF–10µF bulk MLCC or electrolytic per supply rail
- VDDA (analog supply) — additional filtering with ferrite bead

Rules:
- Capacitor must be on same layer as MCU if possible
- Via to ground plane must be as short as possible
- Do NOT daisy-chain decoupling caps — each must have its own via to GND plane
"""

COMPONENTS_PER_VCC_PIN = [
    {"ref": "C?", "value": "100nF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
     "note": "Place one per VCC/VDD pin. LCSC: C14663"},
]

BULK_CAP = {
    "ref": "C?", "value": "4.7uF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
    "note": "One per supply rail. X5R or better. LCSC: C19666",
}

VDDA_FILTER = [
    {"ref": "FB?", "value": "600Ω@100MHz", "footprint": "Inductor_SMD:L_0402_1005Metric",
     "note": "Ferrite bead between VCC and VDDA. LCSC: C1015",
     "example_part": "BLM15AG601SN1D"},
    {"ref": "C?", "value": "1uF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
     "note": "Post-ferrite VDDA bulk cap. LCSC: C52923"},
    {"ref": "C?", "value": "10nF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
     "note": "Post-ferrite VDDA HF decoupling cap."},
]

STM32_POWER_PINS_EXAMPLE = {
    "STM32F103C8T6": {
        "VDD_pins": ["VDD (pin 1)", "VDD (pin 24)", "VDD (pin 36)", "VDD (pin 48)"],
        "VDDA_pins": ["VDDA (pin 5)"],
        "GND_pins": ["VSS", "VSSA"],
        "decoupling_caps_needed": 4,
        "vdda_filter": True,
    }
}

NOTES = """
PCB Layout Rules:
1. Place each 100nF cap within 0.5mm of its VCC pin
2. Connect cap GND directly to nearest GND via — not to GND trace
3. Keep cap between MCU pin and supply trace (series with supply, shunt to GND)
4. Ferrite bead for VDDA: place FB between VCC plane and VDDA pin
5. 10µF bulk cap can be placed up to 5mm away — less critical

Common Mistake: Placing all decoupling caps in a row away from MCU and sharing
one GND via. This defeats the purpose — each cap needs its own low-inductance GND path.
"""
