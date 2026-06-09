from pathlib import Path
from unittest.mock import MagicMock
from backend.services.kicad_libs import LibraryIndex, SymbolRef
from backend.services.symbol_resolver import SymbolResolver, ResolvedSymbol


def test_resolver_prefers_library_hit():
    idx = MagicMock(spec=LibraryIndex)
    idx.search.return_value = [
        SymbolRef(library="Device", name="R", pin_count=2, uri="/x.kicad_sym")
    ]
    r = SymbolResolver(index=idx)
    result = r.resolve(mpn="0603-10k", description="Resistor 10k 0603")
    assert isinstance(result, ResolvedSymbol)
    assert result.kind == "library"
    assert result.library == "Device"
    assert result.name == "R"


def test_resolver_falls_back_to_procedural_when_no_hit():
    idx = MagicMock(spec=LibraryIndex)
    idx.search.return_value = []
    r = SymbolResolver(index=idx)
    result = r.resolve(mpn="STM32F103C8T6", description="ARM MCU")
    assert result.kind == "procedural"
    assert result.pins  # Procedural must include a pin list


def test_resolver_returns_none_when_no_index_and_no_pins():
    r = SymbolResolver(index=None)
    result = r.resolve(mpn="X", description="Y")
    # Without an index, no library hit; without supplied pins, produce a minimal 1-pin placeholder
    assert result.kind == "procedural"
    assert len(result.pins) == 1
