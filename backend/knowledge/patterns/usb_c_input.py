"""Pattern: USB-C input with 5.1k CC pull-downs (UFP, receptacle)."""
from __future__ import annotations

import kicad_sch_api as ksa

from backend.knowledge.protocol import PatternMetadata


class UsbCInput:
    metadata = PatternMetadata(
        id="usb_c_input",
        title="USB-C input (UFP, 5V only)",
        tags=("power", "usb", "usb-c", "input"),
        description=(
            "USB-C receptacle wired as a UFP. Two 5.1k pull-downs on CC1/CC2 "
            "signal the source to provide 5V. VBUS/GND only — no data."
        ),
        inputs={"connector_mpn": "USB-C receptacle MPN"},
    )

    def apply(self, sch: ksa.Schematic, *, connector_mpn: str) -> ksa.Schematic:
        # NOTE: Connector:USB_C_Receptacle_USB2.0 is not in the bundled KiCAD symbol
        # library; Device:R is used as a placeholder for pattern-mechanism testing.
        sch.components.add(
            lib_id="Device:R",
            reference="J1",
            value=connector_mpn,
            position=(100, 100),
        )
        sch.components.add(
            lib_id="Device:R",
            reference="R1",
            value="5.1k",
            position=(120, 100),
        )
        sch.components.add(
            lib_id="Device:R",
            reference="R2",
            value="5.1k",
            position=(120, 110),
        )
        return sch
