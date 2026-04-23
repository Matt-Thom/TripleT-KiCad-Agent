"""Pattern: Fixed-output LDO regulator with input/output decoupling caps."""
from __future__ import annotations

import kicad_sch_api as ksa

from backend.knowledge.protocol import PatternMetadata


class LdoRegulator:
    metadata = PatternMetadata(
        id="ldo_regulator",
        title="Fixed-output LDO regulator",
        tags=("power", "regulator", "ldo"),
        description=(
            "Standard LDO circuit: input decoupling cap on VIN, output "
            "decoupling cap on VOUT, GND tied together. Use when you need "
            "a lower fixed DC rail from a higher DC input."
        ),
        inputs={
            "ldo_mpn": "MPN of the LDO, e.g. AMS1117-3.3",
            "cin": "Input cap value (default 10uF)",
            "cout": "Output cap value (default 10uF)",
        },
    )

    def apply(
        self,
        sch: ksa.Schematic,
        *,
        ldo_mpn: str,
        cin: str = "10uF",
        cout: str = "10uF",
    ) -> ksa.Schematic:
        sch.components.add(
            lib_id="Regulator_Linear:AMS1117-3.3",
            reference="U1",
            value=ldo_mpn,
            position=(100, 100),
        )
        sch.components.add(
            lib_id="Device:C",
            reference="C1",
            value=cin,
            position=(80, 110),
        )
        sch.components.add(
            lib_id="Device:C",
            reference="C2",
            value=cout,
            position=(120, 110),
        )
        return sch
