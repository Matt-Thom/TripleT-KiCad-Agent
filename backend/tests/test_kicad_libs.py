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
