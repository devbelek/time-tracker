"""Сквозные тесты: настоящий сервер на свободном порту и настоящий браузер (Chromium через Playwright).

Запуск: make e2e (нужны requirements-e2e.txt и `playwright install chromium`).
Обычный `pytest` эти тесты пропускает, поэтому для основных проверок браузер не нужен.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import Browser, Page, sync_playwright

from app.db import connect
from app.repository import Repository

ROOT = Path(__file__).resolve().parents[2]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Server:
    """Приложение в отдельном процессе с собственной базой, чтобы тесты не влияли друг на друга."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.port = free_port()
        self.proc: subprocess.Popen[bytes] | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        env = {**os.environ, "TIMETRACKER_DB": str(self.db_path), "TIMETRACKER_LOG_LEVEL": "WARNING"}
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--log-level",
            "warning",
        ]
        self.proc = subprocess.Popen(command, cwd=ROOT, env=env)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("Сервер завершился при запуске")
            try:
                urllib.request.urlopen(f"{self.url}/health", timeout=1).close()
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("Сервер не ответил на /health за 15 секунд")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=10)

    def restart(self) -> None:
        """Полная остановка и новый запуск процесса на той же базе и порту."""
        self.stop()
        self.start()

    def seed(self, fill: Callable[[Repository], None]) -> None:
        """Подготовить данные напрямую в базе (сервер при этом может работать)."""
        with closing(connect(self.db_path)) as conn:
            fill(Repository(conn))


@pytest.fixture
def server(tmp_path: Path) -> Iterator[Server]:
    srv = Server(tmp_path / "e2e.db")
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser: Browser, server: Server) -> Iterator[Page]:
    # Фиксированные часовой пояс и язык: тесты границ суток не зависят от машины, где они запущены
    context = browser.new_context(
        timezone_id="Asia/Bishkek",
        locale="ru-RU",
        color_scheme="light",
        viewport={"width": 1000, "height": 900},
    )
    page = context.new_page()
    page.errors = []  # type: ignore[attr-defined]
    page.on("pageerror", lambda exc: page.errors.append(f"pageerror: {exc}"))  # type: ignore[attr-defined]
    page.on(
        "console",
        lambda msg: (
            page.errors.append(f"console.{msg.type}: {msg.text}")  # type: ignore[attr-defined]
            if msg.type == "error"
            else None
        ),
    )
    page.goto(server.url)
    yield page
    context.close()
