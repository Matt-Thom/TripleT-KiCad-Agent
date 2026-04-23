"""Pattern: I2C pull-up resistors on SDA/SCL."""
from __future__ import annotations

import kicad_sch_api as ksa

from backend.knowledge.protocol import PatternMetadata


class I2cPullups:
    metadata = PatternMetadata(
        id="i2c_pullups",
        title="I2C pull-up resistors",
        tags=["i2c", "bus", "pullup", "digital"],
        description=(
            "A pair of pull-up resistors from SDA and SCL to VCC. 4.7k is a safe "
            "default for 3.3V standard-mode; use 2.2k for fast-mode or heavy bus "
            "capacitance."
        ),
        inputs={"value": "Resistor value (default 4.7k)"},
    )

    def apply(self, sch: ksa.Schematic, *, value: str = "4.7k") -> ksa.Schematic:
        sch.components.add(
            lib_id="Device:R",
            reference="RSDA",
            value=value,
            position=(100, 100),
        )
        sch.components.add(
            lib_id="Device:R",
            reference="RSCL",
            value=value,
            position=(110, 100),
        )
        return sch
