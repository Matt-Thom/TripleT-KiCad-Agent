"""Pattern: MCU reset circuit (pull-up + decoupling cap + optional button)."""
from __future__ import annotations

import kicad_sch_api as ksa

from backend.knowledge.protocol import PatternMetadata


class McuReset:
    metadata = PatternMetadata(
        id="mcu_reset",
        title="MCU reset network",
        tags=["mcu", "reset", "digital"],
        description=(
            "Pull-up on NRST to VCC with a 100nF decoupling cap to GND and an "
            "active-low tactile button. Protects against spurious resets and "
            "provides a manual reset option."
        ),
        inputs={"pullup": "Pull-up value (default 10k)"},
    )

    def apply(self, sch: ksa.Schematic, *, pullup: str = "10k") -> ksa.Schematic:
        sch.components.add(
            lib_id="Device:R",
            reference="R1",
            value=pullup,
            position=(100, 100),
        )
        sch.components.add(
            lib_id="Device:C",
            reference="C1",
            value="100nF",
            position=(110, 100),
        )
        sch.components.add(
            lib_id="Switch:SW_Push",
            reference="SW1",
            value="",
            position=(120, 100),
        )
        return sch
