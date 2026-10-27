"""Бизнес-логика: сотрудники, таймеры, отчёт. Ничего не знает про HTTP."""
import sqlite3
from datetime import UTC, datetime


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class InvalidPeriod(Exception):
    pass


# Разумные границы периода: 1970-01-01 .. 2100-01-01. Без них крайние даты (год 1 или 9999
# со смещением часового пояса) выходят за диапазон datetime при сборке ответа.
MIN_TS = 0
MAX_TS = 4_102_444_800


def _dt(ts: int | None) -> datetime | None:
    return None if ts is None else datetime.fromtimestamp(ts, tz=UTC)


def _normalize_name(name: str) -> str:
    """Схлопываем повторные пробелы: «Анна   Петрова» и «Анна Петрова» это один человек."""
    return " ".join(name.split())


# ---------- сотрудники ----------

def add_employee(conn: sqlite3.Connection, name: str, now: int) -> dict:
    display = _normalize_name(name)
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO employees(name, name_key, created_at) VALUES (?, ?, ?)",
                (display, display.casefold(), now),
            )
    except sqlite3.IntegrityError:
        raise Conflict(f"Сотрудник «{display}» уже добавлен") from None
    return {"id": cur.lastrowid, "name": display, "running": None}


def list_employees(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.id, e.name, t.id AS entry_id, t.description, t.started_at
        FROM employees e
        LEFT JOIN time_entries t ON t.employee_id = e.id AND t.stopped_at IS NULL
        ORDER BY e.name_key
        """
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "running": None
            if r["entry_id"] is None
            else {
                "entry_id": r["entry_id"],
                "description": r["description"],
                "started_at": _dt(r["started_at"]),
            },
        }
        for r in rows
    ]


def _require_employee(conn: sqlite3.Connection, employee_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if row is None:
        raise NotFound("Сотрудник не найден")
    return row


# ---------- таймер ----------

def start_timer(conn: sqlite3.Connection, employee_id: int, description: str, now: int) -> dict:
    _require_employee(conn, employee_id)
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO time_entries(employee_id, description, started_at) VALUES (?, ?, ?)",
                (employee_id, description, now),
            )
    except sqlite3.IntegrityError:
        # сработал уникальный индекс: таймер у этого сотрудника уже идёт
        raise Conflict("Таймер уже запущен. Сначала остановите текущий") from None
    return {"entry_id": cur.lastrowid, "description": description, "started_at": _dt(now)}


def stop_timer(conn: sqlite3.Connection, employee_id: int, now: int) -> dict:
    _require_employee(conn, employee_id)
    with conn:
        # MAX(started_at, ?): страховка на случай, если системные часы откатились назад
        row = conn.execute(
            """
            UPDATE time_entries SET stopped_at = MAX(started_at, ?)
            WHERE employee_id = ? AND stopped_at IS NULL
            RETURNING id, description, started_at, stopped_at
            """,
            (now, employee_id),
        ).fetchone()
    if row is None:
        raise Conflict("Таймер не запущен")
    return {
        "id": row["id"],
        "description": row["description"],
        "started_at": _dt(row["started_at"]),
        "stopped_at": _dt(row["stopped_at"]),
        "seconds": row["stopped_at"] - row["started_at"],
    }


# ---------- отчёт ----------

def build_report(
    conn: sqlite3.Connection,
    period_start: int,
    period_end: int,
    now: int,
    employee_id: int | None = None,
) -> dict:
    """Отчёт за период [period_start, period_end).

    В сумму идёт только та часть записи, которая попала в период: запись, начатая
    до полуночи и законченная после, делится по границе. Идущий таймер считается до «сейчас».
    """
    if period_start >= period_end:
        raise InvalidPeriod("Начало периода должно быть раньше его конца")
    if period_start < MIN_TS or period_end > MAX_TS:
        raise InvalidPeriod("Период должен укладываться в 1970-2100 годы")

    if employee_id is not None:
        _require_employee(conn, employee_id)
        employees = conn.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,))
    else:
        employees = conn.execute("SELECT id, name FROM employees ORDER BY name_key")
    result = {r["id"]: {"id": r["id"], "name": r["name"], "total_seconds": 0, "entries": []}
              for r in employees.fetchall()}

    entries = conn.execute(
        """
        SELECT id, employee_id, description, started_at, stopped_at
        FROM time_entries
        WHERE started_at < :end AND COALESCE(stopped_at, :now) > :start
        ORDER BY started_at, id
        """,
        {"start": period_start, "end": period_end, "now": now},
    ).fetchall()

    for e in entries:
        emp = result.get(e["employee_id"])
        if emp is None:  # отчёт по одному сотруднику
            continue
        finish = e["stopped_at"] if e["stopped_at"] is not None else now
        seconds = max(0, min(finish, period_end) - max(e["started_at"], period_start))
        emp["entries"].append(
            {
                "id": e["id"],
                "description": e["description"],
                "started_at": _dt(e["started_at"]),
                "stopped_at": _dt(e["stopped_at"]),
                "seconds": seconds,
            }
        )
        emp["total_seconds"] += seconds

    employees_out = list(result.values())
    return {
        "period_from": _dt(period_start),
        "period_to": _dt(period_end),
        "total_seconds": sum(e["total_seconds"] for e in employees_out),
        "employees": employees_out,
    }
