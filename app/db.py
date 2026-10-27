"""Подключение к SQLite и версионные миграции схемы."""

import sqlite3
from pathlib import Path

# Каждая миграция применяется один раз, версия хранится в `PRAGMA user_version`.
# Менять уже выпущенную миграцию нельзя: новые изменения схемы добавляются новым элементом списка.
MIGRATIONS: list[str] = [
    # 1: первая версия схемы. `IF NOT EXISTS` нужен, чтобы подхватить базы,
    # созданные до появления версионирования (там user_version равен 0, но таблицы уже есть).
    """
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
    """,
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    # FastAPI открывает соединение в одном потоке пула, а обрабатывает запрос в другом.
    # Соединение у каждого запроса своё и параллельно не используется, поэтому переносить его
    # между потоками безопасно.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> None:
    """Доводит схему до последней версии. Безопасно вызывать при каждом старте."""
    current = schema_version(conn)
    if current > len(MIGRATIONS):
        raise RuntimeError(
            f"База создана более новой версией приложения (схема {current}, поддерживается {len(MIGRATIONS)})"
        )
    for target in range(current + 1, len(MIGRATIONS) + 1):
        try:
            # executescript сам завершает открытую транзакцию, поэтому BEGIN/COMMIT пишем внутри скрипта:
            # миграция и новая версия схемы применяются вместе или не применяются вовсе
            conn.executescript(f"BEGIN;\n{MIGRATIONS[target - 1]}\nPRAGMA user_version = {target};\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        migrate(conn)
    finally:
        conn.close()
