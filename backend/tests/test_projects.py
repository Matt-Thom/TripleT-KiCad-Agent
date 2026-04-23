import pytest

from backend.db import init_db


@pytest.mark.asyncio
async def test_init_db_creates_sqlite_file(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")

    import backend.db as dbmod

    dbmod._engine = None
    dbmod._session_factory = None

    await init_db()

    assert db_path.exists()
