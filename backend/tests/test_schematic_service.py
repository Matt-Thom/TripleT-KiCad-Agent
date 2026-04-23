import os
from backend.services.schematic import SchematicService


def test_generate_single_component_produces_valid_sch(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    file_path = service.generate_single_component_sch(
        mpn="STM32F103C8T6", supplier_id="C8734"
    )
    assert os.path.exists(file_path)
    content = open(file_path).read()
    # KiCad 9 header
    assert "(kicad_sch" in content
    assert "(version" in content
    # MPN must appear as a Value property
    assert "STM32F103C8T6" in content
    # At least one pin should exist in the placeholder fallback
    assert "(pin " in content


def test_generate_single_component_sanitizes_filename(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    file_path = service.generate_single_component_sch(
        mpn="../../etc/passwd", supplier_id="C1"
    )
    # File must be inside tmp_path, not traversed out
    assert str(tmp_path) in file_path
    assert "/etc/passwd" not in file_path


def test_generate_single_component_uses_library_hit_when_available(tmp_path, monkeypatch):
    # Point the service at the fixture sym-lib-table; 'R' is in Device.kicad_sym
    fixture_table = str(
        (os.path.dirname(__file__) + "/fixtures/sym-lib-table")
    )
    monkeypatch.setenv("KICAD_SYM_LIB_TABLE", fixture_table)

    service = SchematicService(output_dir=str(tmp_path))
    path = service.generate_single_component_sch(mpn="R", supplier_id="C1")
    content = open(path).read()
    # A library-backed component references (lib_id "Device:R")
    assert 'lib_id "Device:R"' in content or "Device:R" in content
