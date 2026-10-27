"""HTTP-маршруты. Тонкий слой: разбор запроса, вызов сценария, ответ."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi import Path as PathParam
from pydantic import AwareDatetime

from .db import connect
from .repository import Repository
from .schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeesOut,
    EntryOut,
    ReportOut,
    RunningTimerOut,
    TimerStart,
)
from .service import TimeTracker

# SQLite хранит целые в 64 битах; больший id вызвал бы ошибку 500 вместо «не найден»
MAX_ID = 2**63 - 1
EmployeeId = Annotated[int, PathParam(ge=1, le=MAX_ID)]


def get_tracker(request: Request) -> Iterator[TimeTracker]:
    """Соединение с БД живёт ровно один запрос."""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield TimeTracker(Repository(conn), request.app.state.clock)
    finally:
        conn.close()


Tracker = Annotated[TimeTracker, Depends(get_tracker)]

router = APIRouter(prefix="/api")


@router.get("/employees", response_model=EmployeesOut)
def list_employees(tracker: Tracker) -> dict[str, object]:
    return {"server_time": tracker.now(), "employees": tracker.list_employees()}


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def add_employee(body: EmployeeCreate, tracker: Tracker) -> object:
    return tracker.add_employee(body.name)


@router.post("/employees/{employee_id}/timer/start", response_model=RunningTimerOut, status_code=201)
def start_timer(employee_id: EmployeeId, body: TimerStart, tracker: Tracker) -> object:
    return tracker.start_timer(employee_id, body.description)


@router.post("/employees/{employee_id}/timer/stop", response_model=EntryOut)
def stop_timer(employee_id: EmployeeId, tracker: Tracker) -> object:
    return tracker.stop_timer(employee_id)


@router.get("/report", response_model=ReportOut)
def report(
    tracker: Tracker,
    period_from: Annotated[AwareDatetime, Query(alias="from")],
    period_to: Annotated[AwareDatetime, Query(alias="to")],
    employee_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None,
) -> object:
    return tracker.report(int(period_from.timestamp()), int(period_to.timestamp()), employee_id)
