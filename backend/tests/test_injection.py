import pytest
import os
import shutil
from backend.services.schematic import SchematicService

@pytest.fixture
def schematic_service():
    test_dir = "backend/tests/generated_schematics_test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    service = SchematicService(output_dir=test_dir)
    yield service
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def test_sexp_injection_protection(schematic_service):
    """
    Test that malicious MPNs containing quotes and backslashes are properly escaped
    in the generated S-Expression file.
    """
    # 1. Quote Injection
    malicious_mpn = 'My"Name'
    supplier_id = '123'

    filepath = schematic_service.generate_single_component_sch(malicious_mpn, supplier_id)

    with open(filepath, 'r') as f:
        content = f.read()

    # We expect the quote to be escaped as \"
    assert '(property "Value" "My\\"Name"' in content
    # We expect it NOT to be the raw injection
    assert '(property "Value" "My"Name"' not in content

    # 2. Backslash Injection
    # MPN = Test\Value -> Escaped = Test\\Value
    malicious_mpn_slash = 'Test\\Value'
    filepath_slash = schematic_service.generate_single_component_sch(malicious_mpn_slash, supplier_id)

    with open(filepath_slash, 'r') as f:
        content_slash = f.read()

    # We expect backslash to be escaped as \\ (so in python string literal for assertion it is "\\\\")
    # In the file it should look like "Test\\Value"
    assert 'Test\\\\Value' in content_slash
