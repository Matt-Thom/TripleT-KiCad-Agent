from pathlib import Path
from backend.services.kicad_libs import parse_sym_lib_table, LibraryEntry

FIXTURE = Path(__file__).parent / "fixtures" / "sym-lib-table"


def test_parse_sym_lib_table_returns_two_entries():
    entries = parse_sym_lib_table(FIXTURE)
    assert len(entries) == 2
    names = [e.name for e in entries]
    assert "Device" in names
    assert "MCU_ST_STM32F1" in names


def test_parse_sym_lib_table_expands_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("KICAD9_SYMBOL_DIR", str(tmp_path))
    entries = parse_sym_lib_table(FIXTURE)
    stm_entry = next(e for e in entries if e.name == "MCU_ST_STM32F1")
    assert str(tmp_path) in stm_entry.uri


def test_parse_sym_lib_table_handles_kiprjmod(tmp_path):
    # KIPRJMOD resolves to the directory containing the sym-lib-table itself
    entries = parse_sym_lib_table(FIXTURE)
    device_entry = next(e for e in entries if e.name == "Device")
    assert str(FIXTURE.parent) in device_entry.uri


def test_library_entry_is_a_dataclass_like_object():
    entry = LibraryEntry(name="X", uri="/path.kicad_sym", type="KiCad", descr="d")
    assert entry.name == "X"
    assert entry.uri == "/path.kicad_sym"


from backend.services.kicad_libs import LibraryIndex


def test_library_index_finds_symbol_by_name(tmp_path):
    index = LibraryIndex.from_table(FIXTURE)
    hit = index.find_symbol(library="Device", name="R")
    assert hit is not None
    assert hit.library == "Device"
    assert hit.name == "R"
    assert hit.pin_count == 2


def test_library_index_returns_none_for_missing_symbol():
    index = LibraryIndex.from_table(FIXTURE)
    hit = index.find_symbol(library="Device", name="NonExistent")
    assert hit is None


def test_library_index_search_by_keyword_matches_value_or_name():
    index = LibraryIndex.from_table(FIXTURE)
    hits = index.search("R")
    assert any(h.library == "Device" and h.name == "R" for h in hits)
