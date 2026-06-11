import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import init_db, get_session


def _reset_db_env(tmp_path, monkeypatch, name: str = "test.db"):
    db_path = tmp_path / name
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import backend.db as dbmod

    dbmod._engine = None
    dbmod._session_factory = None
    return db_path


def _client(tmp_path, monkeypatch, name: str = "app.db") -> TestClient:
    """Build a TestClient with an isolated SQLite DB.

    Resets the module-level engine/session cache so that the startup hook in
    ``backend.main`` binds to the per-test database URL.
    """
    _reset_db_env(tmp_path, monkeypatch, name=name)
    from backend.main import app

    return TestClient(app)


@pytest.mark.asyncio
async def test_init_db_creates_sqlite_file(tmp_path, monkeypatch):
    db_path = _reset_db_env(tmp_path, monkeypatch)

    await init_db()

    assert db_path.exists()


@pytest.mark.asyncio
async def test_project_model_roundtrip(tmp_path, monkeypatch):
    _reset_db_env(tmp_path, monkeypatch, name="roundtrip.db")

    from backend.models.project import BomItem, Project

    await init_db()

    async with get_session() as session:
        project = Project(name="Demo")
        session.add(project)
        await session.commit()
        await session.refresh(project)

        item = BomItem(
            project_id=project.id,
            mpn="LM1117-3.3",
            manufacturer="TI",
            description="LDO 3.3V",
            supplier="LCSC",
            supplier_part_number="C6186",
            quantity=2,
        )
        session.add(item)
        await session.commit()

    async with get_session() as session:
        rows = (await session.execute(select(BomItem))).scalars().all()
        assert len(rows) == 1
        assert rows[0].mpn == "LM1117-3.3"
        assert rows[0].quantity == 2
        assert rows[0].project_id == project.id


def test_default_project_exists_on_startup(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert any(p["name"] == "Default" for p in projects)


def test_bom_add_and_list(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        payload = {
            "mpn": "LM1117-3.3",
            "manufacturer": "TI",
            "description": "LDO 3.3V",
            "supplier": "LCSC",
            "supplier_part_number": "C6186",
            "quantity": 3,
        }
        post = client.post(f"/api/projects/{project_id}/bom", json=payload)
        assert post.status_code == 201, post.text
        created = post.json()
        assert created["id"]
        assert created["quantity"] == 3

        listed = client.get(f"/api/projects/{project_id}/bom")
        assert listed.status_code == 200
        body = listed.json()
        assert len(body) == 1
        assert body[0]["mpn"] == "LM1117-3.3"
        assert body[0]["quantity"] == 3


def test_bom_delete(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        post = client.post(
            f"/api/projects/{project_id}/bom",
            json={
                "mpn": "NE555",
                "supplier": "LCSC",
                "supplier_part_number": "C7593",
            },
        )
        assert post.status_code == 201
        item_id = post.json()["id"]

        delete = client.delete(f"/api/projects/{project_id}/bom/{item_id}")
        assert delete.status_code == 204

        listed = client.get(f"/api/projects/{project_id}/bom").json()
        assert listed == []


def test_bom_update_quantity(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        post = client.post(
            f"/api/projects/{project_id}/bom",
            json={
                "mpn": "NE555",
                "supplier": "LCSC",
                "supplier_part_number": "C7593",
                "quantity": 1,
            },
        )
        assert post.status_code == 201
        item_id = post.json()["id"]

        # Update quantity
        put = client.put(
            f"/api/projects/{project_id}/bom/{item_id}",
            json={"quantity": 5},
        )
        assert put.status_code == 200, put.text
        updated = put.json()
        assert updated["quantity"] == 5

        # Check listed quantity
        listed = client.get(f"/api/projects/{project_id}/bom").json()
        assert len(listed) == 1
        assert listed[0]["quantity"] == 5

        # Try setting invalid quantity
        put_invalid = client.put(
            f"/api/projects/{project_id}/bom/{item_id}",
            json={"quantity": 0},
        )
        assert put_invalid.status_code == 422


def test_chat_persists_user_and_assistant_messages(tmp_path, monkeypatch):
    async def fake_get_response(_messages, project_id=None):
        return "Hello from the assistant."

    from backend import main as main_mod

    monkeypatch.setattr(main_mod.ai_service, "get_response", fake_get_response)

    with _client(tmp_path, monkeypatch) as client:
        project_id = client.get("/api/projects").json()[0]["id"]

        resp = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hello there"}]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"content": "Hello from the assistant."}

        messages = client.get(f"/api/projects/{project_id}/messages").json()
        roles = [m["role"] for m in messages]
        contents = [m["content"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles
        assert "Hello there" in contents
        assert "Hello from the assistant." in contents
