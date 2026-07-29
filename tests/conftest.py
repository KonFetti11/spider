"""
Pytest-Fixtures für isolierte DB-/API-Tests.

Jeder Test bekommt eine frische SQLite-Datei in einem tmp-Verzeichnis –
kein Live-Server, keine geteilte .spider/spider.db.
"""

from __future__ import annotations

import pytest

from spider.db.database import Database
import spider.db.database as database_module


@pytest.fixture
def db(tmp_path):
    """Frische Database-Instanz auf einer tmp-Datei."""
    return Database(tmp_path / "test.db")


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """
    TestClient gegen spider.server.api.app, gebunden an eine frische tmp-DB.

    get_db() cached eine Singleton-Instanz im Modul – die wird pro Test
    zurückgesetzt, damit Tests sich nicht gegenseitig beeinflussen.
    """
    from fastapi.testclient import TestClient
    from spider.server.api import app

    monkeypatch.setenv("SPIDER_DB_PATH", str(tmp_path / "api_test.db"))
    database_module._db_instance = None
    yield TestClient(app)
    database_module._db_instance = None
