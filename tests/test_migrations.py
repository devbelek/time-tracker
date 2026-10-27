import sqlite3

import pytest

from app.db import MIGRATIONS, connect, init_db, migrate, schema_version

# Схема так, как её создавала первая опубликованная версия приложения: без user_version
LEGACY_SCHEMA = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL
);
CREATE TABLE time_entries (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    description TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    stopped_at INTEGER,
    CHECK (stopped_at IS NULL OR stopped_at >= started_at)
);
CREATE UNIQUE INDEX one_running_timer_per_employee ON time_entries(employee_id) WHERE stopped_at IS NULL;
CREATE INDEX entries_by_start ON time_entries(started_at);
"""


def test_fresh_database_gets_latest_schema_version(db_path):
    init_db(db_path)
    conn = connect(db_path)
    assert schema_version(conn) == len(MIGRATIONS)
    conn.close()


def test_migration_is_idempotent(db_path):
    init_db(db_path)
    init_db(db_path)  # повторный старт приложения ничего не ломает
    conn = connect(db_path)
    assert schema_version(conn) == len(MIGRATIONS)
    conn.close()


def test_legacy_database_is_upgraded_without_losing_data(db_path):
    legacy = sqlite3.connect(db_path)
    legacy.executescript(LEGACY_SCHEMA)
    legacy.execute("INSERT INTO employees VALUES (1, 'Анна Петрова', 'анна петрова', 0)")
    legacy.execute("INSERT INTO time_entries VALUES (1, 1, 'Старая задача', 100, 200)")
    legacy.commit()
    assert legacy.execute("PRAGMA user_version").fetchone()[0] == 0
    legacy.close()

    init_db(db_path)

    conn = connect(db_path)
    assert schema_version(conn) == len(MIGRATIONS)
    assert conn.execute("SELECT name FROM employees").fetchone()["name"] == "Анна Петрова"
    assert conn.execute("SELECT description FROM time_entries").fetchone()["description"] == "Старая задача"
    conn.close()


def test_database_from_newer_app_version_is_refused(db_path):
    conn = connect(db_path)
    conn.execute(f"PRAGMA user_version = {len(MIGRATIONS) + 1}")
    with pytest.raises(RuntimeError, match="более новой версией"):
        migrate(conn)
    conn.close()


def test_failed_migration_is_rolled_back(db_path, monkeypatch):
    broken = ["CREATE TABLE half_done (id INTEGER); THIS IS NOT SQL;"]
    monkeypatch.setattr("app.db.MIGRATIONS", broken)
    conn = connect(db_path)
    with pytest.raises(sqlite3.Error):
        migrate(conn)
    # ни таблица, ни новая версия схемы не остались
    assert schema_version(conn) == 0
    assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'half_done'").fetchone() is None
    conn.close()
