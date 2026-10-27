from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

T0 = 1_700_000_000  # 2023-11-14 22:13:20 UTC, произвольная точка отсчёта


class FakeClock:
    """Управляемые часы: тесты сами решают, сколько «прошло» времени."""

    def __init__(self, now: int = T0):
        self.now = now

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += seconds


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat().replace("+00:00", "Z")


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(db_path, clock):
    return TestClient(create_app(db_path, clock))


@pytest.fixture
def anna(client):
    return client.post("/api/employees", json={"name": "Анна Петрова"}).json()


def report(client, start: int, end: int, **params):
    return client.get("/api/report", params={"from": iso(start), "to": iso(end), **params})
