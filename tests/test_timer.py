from helpers import T0, report


def start(client, employee, description="Вёрстка главной"):
    return client.post(f"/api/employees/{employee['id']}/timer/start", json={"description": description})


def stop(client, employee):
    return client.post(f"/api/employees/{employee['id']}/timer/stop")


def test_start_and_stop_timer(client, clock, anna):
    assert start(client, anna).status_code == 201
    running = client.get("/api/employees").json()["employees"][0]["running"]
    assert running["description"] == "Вёрстка главной"

    clock.advance(90)
    r = stop(client, anna)
    assert r.status_code == 200
    assert r.json()["seconds"] == 90
    assert client.get("/api/employees").json()["employees"][0]["running"] is None


def test_second_start_while_running_is_rejected(client, clock, anna):
    assert start(client, anna, "Первая задача").status_code == 201
    clock.advance(10)

    r = start(client, anna, "Вторая задача")
    assert r.status_code == 409

    # состояние не испорчено: идёт именно первая задача, запись одна
    running = client.get("/api/employees").json()["employees"][0]["running"]
    assert running["description"] == "Первая задача"
    entries = report(client, T0 - 60, T0 + 3600).json()["employees"][0]["entries"]
    assert len(entries) == 1


def test_stop_without_running_timer_is_rejected(client, anna):
    assert stop(client, anna).status_code == 409


def test_double_stop_is_rejected(client, clock, anna):
    start(client, anna)
    clock.advance(5)
    assert stop(client, anna).status_code == 200
    assert stop(client, anna).status_code == 409


def test_can_start_again_after_stop(client, clock, anna):
    start(client, anna, "Раз")
    clock.advance(60)
    stop(client, anna)
    assert start(client, anna, "Два").status_code == 201


def test_different_employees_can_run_timers_simultaneously(client, anna):
    boris = client.post("/api/employees", json={"name": "Борис Иванов"}).json()
    assert start(client, anna).status_code == 201
    assert start(client, boris).status_code == 201


def test_unknown_employee(client):
    assert client.post("/api/employees/999/timer/start", json={"description": "x"}).status_code == 404
    assert client.post("/api/employees/999/timer/stop").status_code == 404


def test_description_is_required(client, anna):
    for bad in ["", "   "]:
        assert start(client, anna, bad).status_code == 422
    assert client.get("/api/employees").json()["employees"][0]["running"] is None


def test_clock_going_backwards_does_not_break_stop(client, clock, anna):
    start(client, anna)
    clock.advance(-30)  # часы сервера откатились
    r = stop(client, anna)
    assert r.status_code == 200
    assert r.json()["seconds"] == 0
