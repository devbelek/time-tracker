"""Точка сборки приложения: настройки, обработка ошибок, маршруты, фронтенд."""

import logging
import sqlite3
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import api, domain
from .config import Settings
from .db import connect, init_db, schema_version
from .repository import Repository
from .schemas import HealthOut
from .service import Clock

STATIC_DIR = Path(__file__).parent / "static"

FIELD_LABELS = {
    "name": "имя сотрудника",
    "description": "описание задачи",
    "from": "начало периода",
    "to": "конец периода",
    "employee_id": "сотрудник",
}

# Фронтенд раздаётся с этого же сервера и ничего не грузит снаружи, поэтому политика строгая.
# Страницы /docs подгружают Swagger UI с CDN, для них политика не ставится.
CSP = "default-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


def create_app(settings: Settings | None = None, *, clock: Clock | None = None) -> FastAPI:
    """Фабрика приложения. `clock` возвращает unix-время в секундах; в тестах его подменяют."""
    settings = settings or Settings.from_env()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db(settings.db_path)

    app = FastAPI(title="Учёт рабочего времени", version="1.0.0")
    app.state.settings = settings
    app.state.clock = clock or (lambda: int(time.time()))

    # ---------- ошибки предметной области -> понятные JSON-ответы ----------

    statuses: dict[type[Exception], int] = {
        domain.NotFound: 404,
        domain.Conflict: 409,
        domain.InvalidPeriod: 422,
    }

    @app.exception_handler(domain.DomainError)
    async def domain_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=statuses.get(type(exc), 400))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        # у битого JSON последний элемент loc это число (позиция в тексте), имени поля нет
        labels = {FIELD_LABELS.get(str(e["loc"][-1]), "формат запроса") for e in exc.errors()}
        return JSONResponse({"detail": "Проверьте поле: " + ", ".join(sorted(labels))}, status_code=422)

    # ---------- заголовки безопасности ----------

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(DOCS_PATHS):
            response.headers["Content-Security-Policy"] = CSP
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    # ---------- маршруты ----------

    app.include_router(api.router)

    @app.get("/health", response_model=HealthOut, responses={503: {"description": "База данных недоступна"}})
    def health() -> object:
        """Проверка живости для Docker и мониторинга: реально обращается к базе."""
        try:
            conn = connect(settings.db_path)
            try:
                Repository(conn).ping()
                return HealthOut(status="ok", schema_version=schema_version(conn))
            finally:
                conn.close()
        except sqlite3.Error:
            return JSONResponse({"status": "unavailable"}, status_code=503)

    # фронтенд; монтируем последним, чтобы не перекрыть API
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
