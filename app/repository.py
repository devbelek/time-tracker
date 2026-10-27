"""Доступ к данным: весь SQL приложения живёт здесь и только здесь."""

import sqlite3
from dataclasses import dataclass

from .domain import Conflict, NotFound


@dataclass(frozen=True)
class EmployeeRow:
    id: int
    name: str


@dataclass(frozen=True)
class EntryRow:
    id: int
    employee_id: int
    description: str
    started_at: int  # unix-секунды, UTC
    stopped_at: int | None


@dataclass(frozen=True)
class RunningRow:
    employee_id: int
    entry_id: int
    description: str
    started_at: int


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ---------- сотрудники ----------

    def add_employee(self, name: str, key: str, now: int) -> EmployeeRow:
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO employees(name, name_key, created_at) VALUES (?, ?, ?)", (name, key, now)
                )
        except sqlite3.IntegrityError:
            raise Conflict(f"Сотрудник «{name}» уже добавлен") from None
        assert cur.lastrowid is not None
        return EmployeeRow(cur.lastrowid, name)

    def get_employee(self, employee_id: int) -> EmployeeRow:
        row = self._conn.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if row is None:
            raise NotFound("Сотрудник не найден")
        return EmployeeRow(row["id"], row["name"])

    def list_employees(self) -> list[EmployeeRow]:
        rows = self._conn.execute("SELECT id, name FROM employees ORDER BY name_key").fetchall()
        return [EmployeeRow(r["id"], r["name"]) for r in rows]

    # ---------- таймеры ----------

    def running_timers(self) -> dict[int, RunningRow]:
        """Идущие сейчас таймеры по id сотрудника."""
        rows = self._conn.execute(
            "SELECT id, employee_id, description, started_at FROM time_entries WHERE stopped_at IS NULL"
        ).fetchall()
        return {
            r["employee_id"]: RunningRow(r["employee_id"], r["id"], r["description"], r["started_at"]) for r in rows
        }

    def start_entry(self, employee_id: int, description: str, now: int) -> RunningRow:
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO time_entries(employee_id, description, started_at) VALUES (?, ?, ?)",
                    (employee_id, description, now),
                )
        except sqlite3.IntegrityError:
            # сработал уникальный индекс: таймер у этого сотрудника уже идёт
            raise Conflict("Таймер уже запущен. Сначала остановите текущий") from None
        assert cur.lastrowid is not None
        return RunningRow(employee_id, cur.lastrowid, description, now)

    def stop_running_entry(self, employee_id: int, now: int) -> EntryRow:
        with self._conn:
            # MAX(started_at, ?): страховка на случай, если системные часы откатились назад
            row = self._conn.execute(
                """
                UPDATE time_entries SET stopped_at = MAX(started_at, ?)
                WHERE employee_id = ? AND stopped_at IS NULL
                RETURNING id, employee_id, description, started_at, stopped_at
                """,
                (now, employee_id),
            ).fetchone()
        if row is None:
            raise Conflict("Таймер не запущен")
        return _entry(row)

    def entries_overlapping(self, start: int, end: int, now: int, employee_id: int | None = None) -> list[EntryRow]:
        """Записи, которые хотя бы частично попадают в период [start, end)."""
        sql = """
            SELECT id, employee_id, description, started_at, stopped_at
            FROM time_entries
            WHERE started_at < :end AND COALESCE(stopped_at, :now) > :start
        """
        params: dict[str, int] = {"start": start, "end": end, "now": now}
        if employee_id is not None:
            sql += " AND employee_id = :employee_id"
            params["employee_id"] = employee_id
        rows = self._conn.execute(sql + " ORDER BY started_at, id", params).fetchall()
        return [_entry(r) for r in rows]

    # ---------- служебное ----------

    def ping(self) -> None:
        self._conn.execute("SELECT 1").fetchone()


def _entry(row: sqlite3.Row) -> EntryRow:
    return EntryRow(row["id"], row["employee_id"], row["description"], row["started_at"], row["stopped_at"])
