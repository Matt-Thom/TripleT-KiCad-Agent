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


def test_generated_schematic_has_balanced_parens_and_required_keys(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    path = service.generate_single_component_sch(mpn="TEST-001", supplier_id="C999")
    content = open(path).read()

    # Balanced parens
    opens = content.count("(")
    closes = content.count(")")
    assert opens == closes, f"Unbalanced parens: {opens} open vs {closes} close"

    # Required KiCad 9 top-level keys
    for key in ("(kicad_sch", "(version", "(generator", "(uuid", "(paper", "(sheet_instances"):
        assert key in content, f"Missing required top-level key: {key}"


def test_generated_schematic_escapes_newline_in_mpn(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    # An MPN containing a newline must not split the S-expression across lines
    path = service.generate_single_component_sch(mpn="EVIL\nINJECT", supplier_id="C1")
    content = open(path).read()

    # The literal newline must not survive inside a (property "Value" ...) line.
    # Look for the Value property line and confirm it stays on one line.
    for line in content.splitlines():
        if '"Value"' in line and "EVIL" in line:
            # INJECT must appear on the same line, as an escaped \n, not a physical newline
            assert "\\n" in line
            assert "INJECT" in line
            break
    else:
        raise AssertionError("Could not find the Value property line containing EVIL")

    # Parens still balanced
    assert content.count("(") == content.count(")")


def test_generate_multi_component_sch_places_and_routes(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    components = [
        {
            "mpn": "AMS1117-3.3",
            "reference": "U1",
            "supplier_id": "C123",
            "description": "3.3V LDO",
            "connections": {
                "3": "5V",
                "2": "3V3",
                "1": "GND"
            }
        },
        {
            "mpn": "C_10uF",
            "reference": "C1",
            "supplier_id": "C456",
            "description": "Decoupling Cap",
            "pins": [
                {"number": "1", "name": "1", "type": "passive"},
                {"number": "2", "name": "2", "type": "passive"}
            ],
            "connections": {
                "1": "3V3",
                "2": "GND"
            }
        }
    ]
    file_path = service.generate_multi_component_sch(components, filename="test_multi.kicad_sch")
    assert os.path.exists(file_path)
    content = open(file_path).read()
    
    # Verify the header keys exist
    assert "(kicad_sch" in content
    # Verify both component references exist
    assert "U1" in content
    assert "C1" in content
    # Verify values exist
    assert "AMS1117-3.3" in content
    assert "C_10uF" in content
    # Verify wires are present in the schematic
    assert "(wire" in content
    
    # Verify balanced parens
    assert content.count("(") == content.count(")")

