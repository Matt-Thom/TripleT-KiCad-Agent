from backend.knowledge.patterns.ldo_regulator import LdoRegulator
from backend.knowledge.protocol import is_pattern


def test_ldo_pattern_is_a_pattern():
    pat = LdoRegulator()
    assert is_pattern(pat)
    assert pat.metadata.id == "ldo_regulator"
    assert "ldo" in pat.metadata.tags


def test_ldo_pattern_apply_produces_schematic_with_three_components(tmp_path):
    import kicad_sch_api as ksa
    pat = LdoRegulator()
    sch = ksa.create_schematic("ldo-test")
    out = pat.apply(sch, ldo_mpn="AMS1117-3.3", cin="10uF", cout="10uF")
    # Three components: 1 LDO + 2 caps
    assert len(out.components) == 3
