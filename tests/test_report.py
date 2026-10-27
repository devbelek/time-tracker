from conftest import T0, iso, report


def track(client, clock, employee, description, seconds):
    client.post(f"/api/employees/{employee['id']}/timer/start", json={"description": description})
    clock.advance(seconds)
    client.post(f"/api/employees/{employee['id']}/timer/stop")


def test_empty_report_without_employees(client):
    r = report(client, T0, T0 + 3600)
    assert r.status_code == 200
    body = r.json()
    assert body["total_seconds"] == 0
    assert body["employees"] == []


def test_empty_report_when_no_entries_in_period(client, clock, anna):
    track(client, clock, anna, "Старая задача", 600)
    far_future = T0 + 10 * 86400
    body = report(client, far_future, far_future + 86400).json()
    assert body["total_seconds"] == 0
    # сотрудник в отчёте остаётся, но с нулём и без записей
    assert body["employees"][0]["name"] == "Анна Петрова"
    assert body["employees"][0]["total_seconds"] == 0
    assert body["employees"][0]["entries"] == []


def test_totals_per_employee(client, clock, anna):
    boris = client.post("/api/employees", json={"name": "Борис Иванов"}).json()
    track(client, clock, anna, "Задача 1", 600)
    track(client, clock, anna, "Задача 2", 300)
    track(client, clock, boris, "Задача 3", 1000)

    body = report(client, T0 - 1, clock.now + 1).json()
    by_name = {e["name"]: e for e in body["employees"]}
    assert by_name["Анна Петрова"]["total_seconds"] == 900
    assert len(by_name["Анна Петрова"]["entries"]) == 2
    assert by_name["Борис Иванов"]["total_seconds"] == 1000
    assert body["total_seconds"] == 1900


def test_entry_crossing_period_boundary_is_split(client, clock, anna):
    # запись идёт T0 .. T0+1000; период захватывает только её середину
    track(client, clock, anna, "Длинная задача", 1000)
    body = report(client, T0 + 200, T0 + 700).json()
    assert body["employees"][0]["total_seconds"] == 500


def test_entry_outside_period_is_not_counted(client, clock, anna):
    track(client, clock, anna, "Задача", 100)  # T0 .. T0+100
    assert report(client, T0 + 100, T0 + 200).json()["total_seconds"] == 0  # период начинается ровно в конце
    assert report(client, T0 - 200, T0).json()["total_seconds"] == 0  # период заканчивается ровно в начале


def test_running_timer_is_counted_until_now(client, clock, anna):
    client.post(f"/api/employees/{anna['id']}/timer/start", json={"description": "Идёт"})
    clock.advance(120)
    body = report(client, T0 - 60, T0 + 3600).json()  # конец периода в будущем
    entry = body["employees"][0]["entries"][0]
    assert entry["stopped_at"] is None
    assert entry["seconds"] == 120  # считаем до «сейчас», а не до конца периода


def test_report_for_single_employee(client, clock, anna):
    boris = client.post("/api/employees", json={"name": "Борис Иванов"}).json()
    track(client, clock, anna, "А", 100)
    track(client, clock, boris, "Б", 200)
    body = report(client, T0 - 1, clock.now + 1, employee_id=boris["id"]).json()
    assert [e["name"] for e in body["employees"]] == ["Борис Иванов"]
    assert body["total_seconds"] == 200
    assert report(client, T0, T0 + 10, employee_id=999).status_code == 404


def test_invalid_period(client):
    assert report(client, T0 + 10, T0).status_code == 422  # конец раньше начала
    assert report(client, T0, T0).status_code == 422  # пустой период
    r = client.get("/api/report", params={"from": "2023-11-14T10:00:00", "to": "2023-11-15T10:00:00"})
    assert r.status_code == 422  # время без часового пояса не принимаем
    assert client.get("/api/report").status_code == 422


def test_timezone_offsets_in_period_are_respected(client, clock, anna):
    track(client, clock, anna, "Задача", 600)
    # тот же момент, записанный со смещением +06:00 (Бишкек)
    local_start = iso(T0 - 100).replace("Z", "+00:00")
    r = client.get("/api/report", params={"from": local_start, "to": iso(T0 + 1000)})
    assert r.status_code == 200
    assert r.json()["total_seconds"] == 600


def test_extreme_period_dates_give_422_not_500(client):
    extremes = [
        {"from": "0001-01-01T00:00:00+14:00", "to": "2023-01-01T00:00:00Z"},
        {"from": "2023-01-01T00:00:00Z", "to": "9999-12-31T23:59:59-12:00"},
        {"from": "0026-10-01T00:00:00Z", "to": "0026-10-02T00:00:00Z"},  # опечатка в годе в поле даты
    ]
    for params in extremes:
        r = client.get("/api/report", params=params)
        assert r.status_code == 422, params
        assert "1970" in r.json()["detail"]
    # границы диапазона включены
    ok = client.get("/api/report", params={"from": "1970-01-01T00:00:00Z", "to": "2100-01-01T00:00:00Z"})
    assert ok.status_code == 200
