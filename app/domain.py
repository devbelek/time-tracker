"""Предметная область: типы, правила и ошибки. Здесь нет ни SQL, ни HTTP, только чистая логика."""

from dataclasses import dataclass
from datetime import datetime

# Допустимые границы периода отчёта: 1970-01-01 .. 2100-01-01. Без них крайние даты (год 1 или 9999
# со смещением часового пояса) выходят за диапазон datetime при сборке ответа.
MIN_TS = 0
MAX_TS = 4_102_444_800


# ---------- ошибки ----------


class DomainError(Exception):
    """Базовая ошибка предметной области. API превращает наследников в HTTP-коды."""


class NotFound(DomainError):
    pass


class Conflict(DomainError):
    pass


class InvalidPeriod(DomainError):
    pass


# ---------- правила ----------


def normalize_name(name: str) -> str:
    """Схлопываем повторные пробелы: «Анна   Петрова» и «Анна Петрова» это один человек."""
    return " ".join(name.split())


def name_key(name: str) -> str:
    """Ключ для поиска дублей. `casefold` понимает кириллицу, в отличие от `COLLATE NOCASE` в SQLite."""
    return normalize_name(name).casefold()


def overlap_seconds(start: int, stop: int | None, window_start: int, window_end: int, now: int) -> int:
    """Сколько секунд записи [start, stop) лежит внутри окна [window_start, window_end).

    Идущий таймер (`stop is None`) считается до `now`.
    """
    end = now if stop is None else stop
    return max(0, min(end, window_end) - max(start, window_start))


@dataclass(frozen=True)
class Period:
    """Период отчёта [start, end) в unix-секундах. Некорректный период создать нельзя."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise InvalidPeriod("Начало периода должно быть раньше его конца")
        if self.start < MIN_TS or self.end > MAX_TS:
            raise InvalidPeriod("Период должен укладываться в 1970-2100 годы")


# ---------- модели результата ----------


@dataclass(frozen=True)
class RunningTimer:
    entry_id: int
    description: str
    started_at: datetime


@dataclass(frozen=True)
class EmployeeStatus:
    id: int
    name: str
    running: RunningTimer | None


@dataclass(frozen=True)
class Entry:
    id: int
    description: str
    started_at: datetime
    stopped_at: datetime | None  # None, если таймер ещё идёт
    seconds: int  # сколько из этой записи попало в выбранный период


@dataclass(frozen=True)
class EmployeeReport:
    id: int
    name: str
    total_seconds: int
    entries: list[Entry]


@dataclass(frozen=True)
class Report:
    period_from: datetime
    period_to: datetime
    total_seconds: int
    employees: list[EmployeeReport]
