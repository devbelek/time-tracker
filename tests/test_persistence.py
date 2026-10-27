import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from conftest import T0, report


def test_data_survives_restart(db_path, clock):
    first = TestClient(create_app(db_path, clock))
    anna = first.post("/api/employees", json={"name": "Анна Петрова"}).json()
    first.post(f"/api/employees/{anna['id']}/timer/start", json={"description": "Задача"})
    clock.advance(300)
    first.post(f"/api/employees/{anna['id']}/timer/stop")
    first.post(f"/api/employees/{anna['id']}/timer/start", json={"description": "Ещё идёт"})
    del first  # «выключили» приложение

    second = TestClient(create_app(db_path, clock))  # «включили» заново на том же файле БД
    employees = second.get("/api/employees").json()["employees"]
    assert [e["name"] for e in employees] == ["Анна Петрова"]
    assert employees[0]["running"]["description"] == "Ещё идёт"  # запущенный таймер тоже пережил перезапуск

    clock.advance(60)
    body = report(second, T0 - 1, clock.now + 1).json()
    assert body["total_seconds"] == 360  # 300 завершённых + 60 идущих
    # и повторно запустить поверх идущего всё так же нельзя
    r = second.post(f"/api/employees/{anna['id']}/timer/start", json={"description": "Дубль"})
    assert r.status_code == 409


def test_one_running_timer_is_enforced_by_the_database_itself(client, db_path, anna):
    """Защита не только в коде API: БД не даст создать второй идущий таймер."""
    client.post(f"/api/employees/{anna['id']}/timer/start", json={"description": "Первый"})
    conn = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO time_entries(employee_id, description, started_at) VALUES (?, 'Второй', ?)",
            (anna["id"], T0),
        )
    conn.close()
