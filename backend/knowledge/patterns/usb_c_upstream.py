"""USB-C Upstream Port (UFP) — device-side connection with CC pull-down resistors.

For a USB-C device (UFP — Upstream Facing Port) that is powered by a host or
charger, the CC lines must have 5.1kΩ pull-down resistors to GND.

This pattern covers USB 2.0 speeds only (no SuperSpeed lanes).
For USB PD negotiation above 5V/0.9A, add a PD controller (e.g. FUSB302).

Key facts:
- CC1 and CC2 each need a 5.1kΩ pull-down to GND (Rd resistors)
- D+ / D- carry USB 2.0 data — 90Ω differential impedance on PCB
- VBUS is the power input (5V nominal, up to 20V with PD)
- Add 33Ω series resistors on D+/D- for USB 2.0 signal quality
- ESD protection on VBUS, D+, D- strongly recommended (e.g. PRTR5V0U2X)
"""

COMPONENTS = [
    # J1: USB-C receptacle  LCSC: C165948 (USB4135-GF-A)
    {"ref": "J1", "value": "USB-C", "footprint": "Connector_USB:USB_C_Receptacle_GCT_USB4135",
     "note": "USB-C mid-mount or top-mount receptacle. LCSC: C165948"},
    # Rd pull-downs (5.1kΩ on CC1 and CC2)
    {"ref": "R1", "value": "5.1k", "footprint": "Resistor_SMD:R_0402_1005Metric",
     "note": "CC1 Rd pull-down. LCSC: C25905"},
    {"ref": "R2", "value": "5.1k", "footprint": "Resistor_SMD:R_0402_1005Metric",
     "note": "CC2 Rd pull-down. LCSC: C25905"},
    # D+/D- series resistors
    {"ref": "R3", "value": "33R", "footprint": "Resistor_SMD:R_0402_1005Metric",
     "note": "D+ series resistor for USB 2.0. LCSC: C25105"},
    {"ref": "R4", "value": "33R", "footprint": "Resistor_SMD:R_0402_1005Metric",
     "note": "D- series resistor for USB 2.0. LCSC: C25105"},
    # ESD protection
    {"ref": "U2", "value": "PRTR5V0U2X", "footprint": "Package_TO_SOT_SMD:SOT-363_SC-70-6",
     "note": "ESD protection for D+/D-. LCSC: C12333"},
    # VBUS decoupling
    {"ref": "C5", "value": "100nF", "footprint": "Capacitor_SMD:C_0402_1005Metric",
     "note": "VBUS decoupling. LCSC: C14663"},
    {"ref": "C6", "value": "10uF", "footprint": "Capacitor_SMD:C_0805_2012Metric",
     "note": "VBUS bulk cap. LCSC: C19702"},
]

NETS = {
    "VBUS": "USB VBUS power (5V from host/charger)",
    "D+": "USB 2.0 data positive",
    "D-": "USB 2.0 data negative",
    "CC1": "USB-C configuration channel 1",
    "CC2": "USB-C configuration channel 2",
    "GND": "Ground",
}

NOTES = """
Important:
- 5.1kΩ CC pull-downs tell the host this is a sink device
- WITHOUT CC resistors, the host will not provide power (USB PD spec requirement)
- For USB 2.0 only — SBU1/SBU2 and SuperSpeed pairs can be left unconnected
- D+/D- traces must be differential pairs: 90Ω impedance, matched length
- Keep D+/D- away from switching supplies and clock traces
- VBUS reverse protection: add P-channel MOSFET or ideal diode if needed
"""
