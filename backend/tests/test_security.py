import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.main import download_file
from fastapi import HTTPException
import os
import shutil

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    base_dir = "generated_schematics"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # Create a safe file
    with open(os.path.join(base_dir, "safe.txt"), "w") as f:
        f.write("This is safe content")

    yield

    # Teardown
    if os.path.exists(os.path.join(base_dir, "safe.txt")):
        os.remove(os.path.join(base_dir, "safe.txt"))

def test_download_safe_file():
    response = client.get("/api/download/safe.txt")
    assert response.status_code == 200
    assert response.content == b"This is safe content"

def test_path_traversal_attack():
    # Attempt to access the parent directory using ".."
    # If ".." is passed in URL, FastAPI might normalize it or not find the route.
    # But if it reaches the handler, it must be rejected.
    response = client.get("/api/download/..")
    # If it is 404, it means it didn't reach the handler (routing), which is safe but doesn't test our fix.
    # If it returns 403, our fix works.
    assert response.status_code in [403, 404]

@pytest.mark.asyncio
async def test_path_traversal_attack_direct_call():
    # Direct call to verify logic independently of routing

    # Case 1: Traversal
    try:
        await download_file(filename="..")
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403
        assert e.detail == "Access denied"

    # Case 2: Absolute path (e.g. /etc/passwd style)
    try:
        abs_path = os.path.abspath("README.md") # Points to repo root
        await download_file(filename=abs_path)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403
        assert e.detail == "Access denied"
