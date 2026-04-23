import pytest
import kicad_sch_api as ksa

from backend.knowledge.patterns.ldo_regulator import LdoRegulator
from backend.knowledge.patterns.usb_c_input import UsbCInput
from backend.knowledge.patterns.i2c_pullups import I2cPullups
from backend.knowledge.patterns.mcu_reset import McuReset
from backend.knowledge.protocol import is_pattern


def test_ldo_pattern_is_a_pattern():
    pat = LdoRegulator()
    assert is_pattern(pat)
    assert pat.metadata.id == "ldo_regulator"
    assert "ldo" in pat.metadata.tags


def test_ldo_pattern_apply_produces_schematic_with_three_components(tmp_path):
    pat = LdoRegulator()
    sch = ksa.create_schematic("ldo-test")
    out = pat.apply(sch, ldo_mpn="AMS1117-3.3", cin="10uF", cout="10uF")
    # Three components: 1 LDO + 2 caps
    assert len(out.components) == 3


@pytest.mark.parametrize(
    "pat_cls,inputs,expected_component_count",
    [
        (UsbCInput, {"connector_mpn": "TYPE-C-31-M-12"}, 3),
        (I2cPullups, {}, 2),
        (McuReset, {}, 3),
    ],
)
def test_patterns_apply_and_produce_expected_components(pat_cls, inputs, expected_component_count):
    sch = ksa.create_schematic("pattern-smoke")
    pat_cls().apply(sch, **inputs)
    assert len(sch.components) == expected_component_count
