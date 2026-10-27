"""Схемы запросов и ответов API (граница между HTTP и предметной областью)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class EmployeeCreate(BaseModel):
    name: Name


class TimerStart(BaseModel):
    description: Description


class Out(BaseModel):
    """Базовый класс ответов: умеет читать поля из dataclass-объектов предметной области."""

    model_config = ConfigDict(from_attributes=True)


class RunningTimerOut(Out):
    entry_id: int
    description: str
    started_at: datetime


class EmployeeOut(Out):
    id: int
    name: str
    running: RunningTimerOut | None


class EmployeesOut(Out):
    server_time: datetime  # чтобы фронтенд показывал время таймера по часам сервера
    employees: list[EmployeeOut]


class EntryOut(Out):
    id: int
    description: str
    started_at: datetime
    stopped_at: datetime | None  # None, если таймер ещё идёт
    seconds: int  # сколько из этой записи попало в выбранный период


class EmployeeReportOut(Out):
    id: int
    name: str
    total_seconds: int
    entries: list[EntryOut]


class ReportOut(Out):
    period_from: datetime
    period_to: datetime
    total_seconds: int
    employees: list[EmployeeReportOut]


class HealthOut(BaseModel):
    status: str
    schema_version: int
