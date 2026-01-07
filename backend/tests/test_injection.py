import pytest
import os
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_injection_vulnerability_repro():
    """
    Test that attempts to inject malicious content into the KiCad file.
    The application should now sanitize the input, so the injection should fail.
    The content should act as a string value, not S-Expression structure.
    """
    # Malicious MPN designed to break out of the string literal in the file content
    payload = 'BadValue" (at 0 0 0)) (property "Injected" "Malicious"'

    supplier_id = "repro_supplier"

    response = client.post(
        "/api/generate/schematic",
        params={"mpn": payload, "supplier_id": supplier_id}
    )

    assert response.status_code == 200

    content = response.content.decode("utf-8")

    print("\nGenerated Content:\n", content)

    # Verify that the injection string was escaped or sanitized.
    # It should NOT appear as a raw property definition.
    # It should appear as an escaped string inside the "Value" property.
    # KiCad escapes quotes as \"

    expected_escaped = 'BadValue\\" (at 0 0 0)) (property \\"Injected\\" \\"Malicious\\"'

    # We verify that our escaped version is present, meaning the injection was neutralized
    assert expected_escaped in content

    # And we verify that the raw unescaped injection is NOT present (except as part of the above)
    # Actually, simplistic string search might find it if we are not careful.
    # But essentially, we want to ensure the S-Expression structure is intact.
    # The property "Injected" should not exist as a key.

    # This regex looks for (property "Injected" "Malicious" literally as a property definition
    # But since we are looking for the exact string, let's just assert that the *structure* is safe.
    # If the quotes are escaped, it's treated as a value.

    assert '(property "Value" "' + expected_escaped + '"' in content

def test_filename_sanitization():
    """
    Test that the filename is sanitized.
    """
    payload = 'bad/filename\\test'
    supplier_id = 'sup'

    response = client.post(
        "/api/generate/schematic",
        params={"mpn": payload, "supplier_id": supplier_id}
    )

    assert response.status_code == 200

    # Check Content-Disposition header for filename
    content_disposition = response.headers["content-disposition"]
    # expected: bad_filename_test_sup.kicad_sch
    assert "bad_filename_test_sup.kicad_sch" in content_disposition
