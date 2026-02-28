"""I2C Bus Pull-up Resistors — correct values for reliable communication.

I2C uses open-drain signalling. SDA and SCL require pull-up resistors to VCC.
Choosing the wrong value causes slow edges (too high) or excess current (too low).

Pull-up value selection:
  R_min = (VCC - VOL_max) / IOL_max   (max sink current per I2C spec)
  R_max = t_rise / (0.8473 × C_bus)  (rise time constraint)

Standard values:
- 100kHz (Standard): 10kΩ (works up to ~400pF bus capacitance)
- 400kHz (Fast): 2.2kΩ–4.7kΩ
- 1MHz (Fast+): 1kΩ (requires VCC ≥ 2.7V, short traces only)

Rule of thumb for most designs (< 5 devices, < 30cm traces):
- 4.7kΩ for 100kHz
- 2.2kΩ for 400kHz
"""

COMPONENTS = {
    "100kHz": [
        {"ref": "R6", "value": "4.7k", "footprint": "Resistor_SMD:R_0402_1005Metric",
         "note": "SDA pull-up to VCC. LCSC: C25900"},
        {"ref": "R7", "value": "4.7k", "footprint": "Resistor_SMD:R_0402_1005Metric",
         "note": "SCL pull-up to VCC. LCSC: C25900"},
    ],
    "400kHz": [
        {"ref": "R6", "value": "2.2k", "footprint": "Resistor_SMD:R_0402_1005Metric",
         "note": "SDA pull-up to VCC (400kHz). LCSC: C25879"},
        {"ref": "R7", "value": "2.2k", "footprint": "Resistor_SMD:R_0402_1005Metric",
         "note": "SCL pull-up to VCC (400kHz). LCSC: C25879"},
    ],
}

NETS = {
    "SDA": "I2C data line (open-drain)",
    "SCL": "I2C clock line (open-drain)",
    "VCC": "Pull-up supply (match to logic level of all devices on bus)",
}

NOTES = """
Common mistakes:
- Using 10kΩ for 400kHz → rise time too slow, communication fails
- Using 1kΩ for 3.3V systems → VOL margin violated, devices may not pull low correctly
- Putting pull-ups at every device instead of once per bus
  → ONLY ONE SET of pull-ups per I2C bus segment

Level shifting:
- If master is 3.3V and device is 5V (or vice versa):
  Use a bidirectional level shifter (e.g. BSS138 MOSFET pair, or PCA9306)
  DO NOT connect 5V I2C directly to 3.3V MCU — risk of damage

Bus capacitance budget:
- Each device adds ~10pF, each 10cm of PCB trace adds ~10pF
- Stay under 400pF for standard mode, 100pF for fast mode with standard pull-ups
- For high-cap buses: use I2C buffer/repeater (e.g. PCA9515)

Pull-up supply voltage:
- Must match the lower of the two device logic levels
- For 3.3V MCU + 3.3V sensor: pull to 3.3V
- For mixed voltage: pull to lower voltage and level shift to higher
"""
