from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, AsyncMock, MagicMock

client = TestClient(app)

def test_search_lcsc_endpoint():
    # Mock data
    mock_data = {
        "components": [
            {
                "lcsc": 12345,
                "mfr": "Test-Resistor",
                "package": "0603",
                "stock": 1000,
                "price": 0.01,
                "description": "10k Resistor",
                "is_basic": True,
                "is_preferred": True
            }
        ]
    }

    # Mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status.return_value = None

    # Mock the client instance
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response

    # Mock the context manager behavior of the client
    # When httpx.AsyncClient() is called, it returns a mock that behaves as an async context manager
    with patch("httpx.AsyncClient", return_value=mock_client_instance) as MockClient:
        # The instance returned by the constructor needs to be an async context manager
        # So __aenter__ returns the instance itself (which has the .get method)
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        response = client.get("/api/search/lcsc?q=resistor")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["mpn"] == "Test-Resistor"
        assert data[0]["supplier"] == "LCSC"
        assert data[0]["stock"] == 1000
        assert data[0]["supplier_part_number"] == "C12345"


def test_search_lcsc_maps_full_rows_with_datasheet():
    # Shape returned by jlcsearch with full=true: raw DB rows including the
    # datasheet column, numeric basic/preferred flags, and tiered price JSON.
    mock_data = {
        "components": [
            {
                "lcsc": 6186,
                "mfr": "AMS1117-3.3",
                "package": "SOT-223",
                "stock": 50000,
                "price": '[{"qFrom": 1, "qTo": 9, "price": 0.1234}]',
                "description": "1A 3.3V LDO",
                "basic": 1,
                "preferred": 0,
                "datasheet": "https://example.com/ams1117.pdf",
                "extra": None,
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client_instance):
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        response = client.get("/api/search/lcsc?q=AMS1117")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        part = data[0]
        assert part["datasheet_url"] == "https://example.com/ams1117.pdf"
        assert part["price"] == 0.1234
        assert part["supplier_part_number"] == "C6186"
        assert part["attributes"]["Basic"] is True
        assert part["attributes"]["Preferred"] is False

        # The request must ask for full rows (that's where the datasheet lives)
        call_kwargs = mock_client_instance.get.call_args.kwargs
        assert call_kwargs["params"]["full"] == "true"
