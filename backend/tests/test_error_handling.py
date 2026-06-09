from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch
import pytest

client = TestClient(app)

def test_exception_leak_fixed():
    """
    Test that the application NO LONGER leaks exception details in 500 errors.
    """
    # We patch the service used by the endpoint
    with patch("backend.services.schematic.schematic_service.generate_single_component_sch") as mock_gen:
        # Simulate an internal error that contains sensitive info
        secret_message = "CRITICAL_FAILURE_DB_HOST_10.0.0.5"
        mock_gen.side_effect = Exception(f"Unexpected error: {secret_message}")

        response = client.post("/api/generate/schematic?mpn=TEST&supplier_id=123")

        assert response.status_code == 500
        # The sensitive info should NOT be leaked
        assert secret_message not in response.json()["detail"]
        # It should return a generic message
        assert response.json()["detail"] == "Internal Server Error"
