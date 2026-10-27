"""HTTP-слой: маршруты FastAPI и раздача фронтенда."""
import os
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Path as PathParam, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AwareDatetime

from . import service
from .db import connect, init_db
from .schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeesOut,
    EntryOut,
    ReportOut,
    RunningTimer,
    TimerStart,
)

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DB = "data/timetracker.db"

# SQLite хранит целые в 64 битах; больший id вызвал бы ошибку 500 вместо «не найден»
MAX_ID = 2**63 - 1
EmployeeId = Annotated[int, PathParam(ge=1, le=MAX_ID)]

FIELD_LABELS = {
    "name": "имя сотрудника",
    "description": "описание задачи",
    "from": "начало периода",
    "to": "конец периода",
    "employee_id": "сотрудник",
}


def create_app(db_path: str | Path | None = None, clock: Callable[[], int] | None = None) -> FastAPI:
    """Фабрика приложения. `clock` возвращает unix-время в секундах; в тестах его подменяют."""
    db_path = db_path or os.environ.get("TIMETRACKER_DB", DEFAULT_DB)
    clock = clock or (lambda: int(time.time()))
    init_db(db_path)

    app = FastAPI(title="Учёт рабочего времени")

    def get_conn():
        conn = connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    Conn = Annotated[sqlite3.Connection, Depends(get_conn)]

    # ---------- ошибки -> понятные JSON-ответы ----------

    @app.exception_handler(service.NotFound)
    async def not_found(_: Request, exc: service.NotFound):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(service.Conflict)
    async def conflict(_: Request, exc: service.Conflict):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(service.InvalidPeriod)
    async def invalid_period(_: Request, exc: service.InvalidPeriod):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        # у битого JSON последний элемент loc это число (позиция в тексте), имени поля нет
        labels = {FIELD_LABELS.get(e["loc"][-1], "формат запроса") for e in exc.errors()}
        return JSONResponse({"detail": "Проверьте поле: " + ", ".join(sorted(labels))}, status_code=422)

    # ---------- маршруты ----------

    @app.get("/api/employees", response_model=EmployeesOut)
    def list_employees(conn: Conn):
        return {
            "server_time": datetime.fromtimestamp(clock(), tz=UTC),
            "employees": service.list_employees(conn),
        }

    @app.post("/api/employees", response_model=EmployeeOut, status_code=201)
    def add_employee(body: EmployeeCreate, conn: Conn):
        return service.add_employee(conn, body.name, clock())

    @app.post("/api/employees/{employee_id}/timer/start", response_model=RunningTimer, status_code=201)
    def start_timer(employee_id: EmployeeId, body: TimerStart, conn: Conn):
        return service.start_timer(conn, employee_id, body.description, clock())

    @app.post("/api/employees/{employee_id}/timer/stop", response_model=EntryOut)
    def stop_timer(employee_id: EmployeeId, conn: Conn):
        return service.stop_timer(conn, employee_id, clock())

    @app.get("/api/report", response_model=ReportOut)
    def report(
        conn: Conn,
        period_from: Annotated[AwareDatetime, Query(alias="from")],
        period_to: Annotated[AwareDatetime, Query(alias="to")],
        employee_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None,
    ):
        return service.build_report(
            conn,
            int(period_from.timestamp()),
            int(period_to.timestamp()),
            clock(),
            employee_id,
        )

    # фронтенд; монтируем последним, чтобы не перекрыть /api
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app

