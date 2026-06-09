import pytest
from fastapi.testclient import TestClient
from backend.db import init_db
from backend.tests.test_projects import _client

def test_block_diagram_endpoints(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        # 1. Get block diagram on empty project should return empty lists
        get_resp = client.get(f"/api/projects/{project_id}/block-diagram")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["blocks"] == []
        assert data["connections"] == []

        # 2. Save block diagram
        payload = {
            "blocks": [
                {"id": "mcu", "type": "MCU", "description": "STM32F4", "voltage_domain": "3.3V"},
                {"id": "ldo", "type": "Regulator", "description": "AMS1117", "voltage_domain": "3.3V"}
            ],
            "connections": [
                {"source_block_id": "ldo", "target_block_id": "mcu", "type": "Power", "description": "3.3V rail"}
            ]
        }
        post_resp = client.post(f"/api/projects/{project_id}/block-diagram", json=payload)
        assert post_resp.status_code == 200
        saved = post_resp.json()
        assert len(saved["blocks"]) == 2
        assert saved["connections"][0]["source_block_id"] == "ldo"

        # 3. Retrieve block diagram again
        get_resp2 = client.get(f"/api/projects/{project_id}/block-diagram")
        assert get_resp2.status_code == 200
        retrieved = get_resp2.json()
        assert len(retrieved["blocks"]) == 2
        assert retrieved["blocks"][0]["id"] == "mcu"


def test_schematic_ir_endpoints(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        # 1. Get schematic IR on empty project should return empty lists
        get_resp = client.get(f"/api/projects/{project_id}/schematic-ir")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["components"] == []
        assert data["nets"] == []

        # 2. Save schematic IR
        payload = {
            "components": [
                {
                    "reference": "U1",
                    "mpn": "AMS1117-3.3",
                    "supplier_id": "C6186",
                    "value": "3.3V LDO",
                    "pins": [
                        {"number": "1", "name": "GND", "type": "power_in"},
                        {"number": "2", "name": "VOUT", "type": "power_out"},
                        {"number": "3", "name": "VIN", "type": "power_in"}
                    ],
                    "block_id": "ldo"
                }
            ],
            "nets": [
                {
                    "name": "3V3",
                    "connections": [{"component_ref": "U1", "pin_number": "2"}]
                }
            ]
        }
        post_resp = client.post(f"/api/projects/{project_id}/schematic-ir", json=payload)
        assert post_resp.status_code == 200
        saved = post_resp.json()
        assert len(saved["components"]) == 1
        assert saved["components"][0]["reference"] == "U1"
        assert saved["nets"][0]["name"] == "3V3"

        # 3. Retrieve schematic IR again
        get_resp2 = client.get(f"/api/projects/{project_id}/schematic-ir")
        assert get_resp2.status_code == 200
        retrieved = get_resp2.json()
        assert len(retrieved["components"]) == 1
        assert retrieved["components"][0]["pins"][1]["name"] == "VOUT"


def test_erc_endpoint(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        # Save an invalid schematic IR (floating inputs)
        payload = {
            "components": [
                {
                    "reference": "U1",
                    "mpn": "TEST_MCU",
                    "supplier_id": "C001",
                    "pins": [{"number": "1", "name": "IN", "type": "input"}]
                }
            ],
            "nets": []
        }
        client.post(f"/api/projects/{project_id}/schematic-ir", json=payload)

        # Retrieve ERC violations
        erc_resp = client.get(f"/api/projects/{project_id}/erc")
        assert erc_resp.status_code == 200
        violations = erc_resp.json()
        assert len(violations) == 1
        assert violations[0]["rule"] == "FLOATING_INPUT"


def test_compile_endpoint_empty_fails(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]
        # Compilation fails on empty Schematic IR
        compile_resp = client.post(f"/api/projects/{project_id}/schematic-ir/compile")
        assert compile_resp.status_code == 400


def test_compile_endpoint_success(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        # Save a schematic IR with U1 and connections
        payload = {
            "components": [
                {
                    "reference": "U1",
                    "mpn": "AMS1117-3.3",
                    "supplier_id": "C6186",
                    "pins": [
                        {"number": "1", "name": "GND", "type": "power_in"},
                        {"number": "2", "name": "VOUT", "type": "power_out"},
                        {"number": "3", "name": "VIN", "type": "power_in"}
                    ]
                }
            ],
            "nets": []
        }
        client.post(f"/api/projects/{project_id}/schematic-ir", json=payload)

        # Call compile
        compile_resp = client.post(f"/api/projects/{project_id}/schematic-ir/compile?filename=test_ir.kicad_sch")
        assert compile_resp.status_code == 200
        data = compile_resp.json()
        assert "download_url" in data
        assert data["filename"] == "test_ir.kicad_sch"
