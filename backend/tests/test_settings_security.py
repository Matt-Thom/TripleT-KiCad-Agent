from fastapi.testclient import TestClient
from backend.main import app
import os

client = TestClient(app)

def test_env_injection_prevented():
    """
    Test that attempts to inject newlines in settings are rejected.
    """
    payload = {
        "openai_api_key": "valid_key\nA_MALICIOUS_VAR=true",
        "default_model": "gemini/gemini-pro"
    }

    response = client.post("/api/settings", json=payload)

    # Expect a 400 Bad Request
    assert response.status_code == 400
    assert "Invalid character" in response.json()["detail"]

    # Verify .env was not modified (or at least check that the malicious var isn't there)
    # Note: Depending on test execution order, .env might have state from previous runs.
    # But since the request failed, it shouldn't have written anything new.
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            content = f.read()
            assert "A_MALICIOUS_VAR=true" not in content

def test_env_quoting():
    """
    Test that valid values are correctly quoted in the .env file.
    """
    payload = {
        "openai_api_key": "key with spaces",
        "default_model": "gemini/gemini-pro"
    }

    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200

    if os.path.exists(".env"):
        with open(".env", "r") as f:
            content = f.read()
            assert "OPENAI_API_KEY='key with spaces'" in content

def test_quote_injection_prevented():
    """
    Test that attempts to inject single quotes to break out of the .env value are rejected.
    """
    payload = {
        "openai_api_key": "val'ue",
        "default_model": "gemini/gemini-pro"
    }

    response = client.post("/api/settings", json=payload)

    # Expect a 400 Bad Request
    assert response.status_code == 400
    assert "Invalid character (single quote)" in response.json()["detail"]
