"""Сценарии использования: связывает правила предметной области, хранилище и часы."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from .domain import (
    EmployeeReport,
    EmployeeStatus,
    Entry,
    Period,
    Report,
    RunningTimer,
    name_key,
    normalize_name,
    overlap_seconds,
)
from .repository import EntryRow, Repository, RunningRow

log = logging.getLogger("timetracker")

Clock = Callable[[], int]  # unix-время в секундах; в тестах подменяется


def to_datetime(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def _running(row: RunningRow) -> RunningTimer:
    return RunningTimer(row.entry_id, row.description, to_datetime(row.started_at))


def _entry(row: EntryRow, seconds: int) -> Entry:
    return Entry(
        id=row.id,
        description=row.description,
        started_at=to_datetime(row.started_at),
        stopped_at=None if row.stopped_at is None else to_datetime(row.stopped_at),
        seconds=seconds,
    )


class TimeTracker:
    def __init__(self, repo: Repository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def now(self) -> datetime:
        return to_datetime(self._clock())

    # ---------- сотрудники ----------

    def add_employee(self, name: str) -> EmployeeStatus:
        display = normalize_name(name)
        row = self._repo.add_employee(display, name_key(display), self._clock())
        log.info("employee added id=%s", row.id)
        return EmployeeStatus(row.id, row.name, running=None)

    def list_employees(self) -> list[EmployeeStatus]:
        running = self._repo.running_timers()
        return [
            EmployeeStatus(e.id, e.name, _running(running[e.id]) if e.id in running else None)
            for e in self._repo.list_employees()
        ]

    # ---------- таймер ----------

    def start_timer(self, employee_id: int, description: str) -> RunningTimer:
        self._repo.get_employee(employee_id)
        row = self._repo.start_entry(employee_id, description, self._clock())
        log.info("timer started employee=%s entry=%s", employee_id, row.entry_id)
        return _running(row)

    def stop_timer(self, employee_id: int) -> Entry:
        self._repo.get_employee(employee_id)
        row = self._repo.stop_running_entry(employee_id, self._clock())
        assert row.stopped_at is not None
        seconds = row.stopped_at - row.started_at
        log.info("timer stopped employee=%s entry=%s seconds=%s", employee_id, row.id, seconds)
        return _entry(row, seconds)

    # ---------- отчёт ----------

    def report(self, start: int, end: int, employee_id: int | None = None) -> Report:
        """Отчёт за период [start, end).

        В сумму идёт только та часть записи, которая попала в период: запись, начатая
        до полуночи и законченная после, делится по границе. Идущий таймер считается до «сейчас».
        """
        period = Period(start, end)
        now = self._clock()

        employees = self._repo.list_employees() if employee_id is None else [self._repo.get_employee(employee_id)]

        entries: dict[int, list[Entry]] = {e.id: [] for e in employees}
        for row in self._repo.entries_overlapping(period.start, period.end, now, employee_id):
            seconds = overlap_seconds(row.started_at, row.stopped_at, period.start, period.end, now)
            entries[row.employee_id].append(_entry(row, seconds))

        reports = [
            EmployeeReport(e.id, e.name, sum(x.seconds for x in entries[e.id]), entries[e.id]) for e in employees
        ]
        return Report(
            period_from=to_datetime(period.start),
            period_to=to_datetime(period.end),
            total_seconds=sum(r.total_seconds for r in reports),
            employees=reports,
        )
