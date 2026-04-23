import pytest
from sqlmodel import select

from backend.db import init_db, get_session


def _reset_db_env(tmp_path, monkeypatch, name: str = "test.db"):
    db_path = tmp_path / name
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import backend.db as dbmod

    dbmod._engine = None
    dbmod._session_factory = None
    return db_path


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
