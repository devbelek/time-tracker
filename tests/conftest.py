import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from helpers import FakeClock


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(db_path, clock):
    return TestClient(create_app(Settings(db_path=db_path), clock=clock))


@pytest.fixture
def anna(client):
    return client.post("/api/employees", json={"name": "Анна Петрова"}).json()
