"""Подключение к SQLite и схема таблиц."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    -- имя в нижнем регистре: по нему ищем дубли (COLLATE NOCASE в SQLite не понимает кириллицу)
    name_key   TEXT    NOT NULL UNIQUE,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS time_entries (
    id          INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    description TEXT    NOT NULL,
    started_at  INTEGER NOT NULL,           -- unix-время в секундах, UTC
    stopped_at  INTEGER,                    -- NULL, пока таймер идёт
    CHECK (stopped_at IS NULL OR stopped_at >= started_at)
);

-- Не больше одного запущенного таймера на сотрудника. Правило живёт в самой БД,
-- поэтому его нельзя обойти даже двумя одновременными запросами.
CREATE UNIQUE INDEX IF NOT EXISTS one_running_timer_per_employee
    ON time_entries(employee_id) WHERE stopped_at IS NULL;

CREATE INDEX IF NOT EXISTS entries_by_start ON time_entries(started_at);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    # FastAPI открывает соединение в одном потоке пула, а обрабатывает запрос в другом.
    # Соединение у каждого запроса своё и параллельно не используется, поэтому переносить его
    # между потоками безопасно.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
    finally:
        conn.close()
