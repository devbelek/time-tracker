"""Схемы запросов и ответов API."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class EmployeeCreate(BaseModel):
    name: Name


class TimerStart(BaseModel):
    description: Description


class RunningTimer(BaseModel):
    entry_id: int
    description: str
    started_at: datetime


class EmployeeOut(BaseModel):
    id: int
    name: str
    running: RunningTimer | None


class EmployeesOut(BaseModel):
    server_time: datetime  # чтобы фронтенд показывал время таймера по часам сервера
    employees: list[EmployeeOut]


class EntryOut(BaseModel):
    id: int
    description: str
    started_at: datetime
    stopped_at: datetime | None  # None, если таймер ещё идёт
    seconds: int  # сколько из этой записи попало в выбранный период


class EmployeeReport(BaseModel):
    id: int
    name: str
    total_seconds: int
    entries: list[EntryOut]


class ReportOut(BaseModel):
    period_from: datetime
    period_to: datetime
    total_seconds: int
    employees: list[EmployeeReport]
