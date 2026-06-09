from backend.services.procedural_symbol import build_procedural_symbol, PinSpec


def test_build_procedural_symbol_returns_sexp_with_pins():
    pins = [
        PinSpec(number="1", name="VCC", type="power_in"),
        PinSpec(number="2", name="GND", type="power_in"),
        PinSpec(number="3", name="IO1", type="bidirectional"),
    ]
    sexp = build_procedural_symbol(name="TEST_MPN", pins=pins)
    assert "(symbol \"TEST_MPN\"" in sexp
    assert "\"VCC\"" in sexp
    assert "\"GND\"" in sexp
    assert "\"IO1\"" in sexp
    # All three pin numbers must appear
    for n in ("1", "2", "3"):
        assert f'"{n}"' in sexp


def test_build_procedural_symbol_escapes_quotes():
    pins = [PinSpec(number="1", name="A", type="input")]
    sexp = build_procedural_symbol(name='weird"mpn', pins=pins)
    assert '\\"' in sexp  # Escaped quote in the name


def test_build_procedural_symbol_rejects_empty_pins():
    import pytest as pt
    with pt.raises(ValueError):
        build_procedural_symbol(name="X", pins=[])
