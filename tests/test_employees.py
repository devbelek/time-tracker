def test_add_and_list_employees(client):
    r = client.post("/api/employees", json={"name": "  Анна   Петрова "})
    assert r.status_code == 201
    assert r.json()["name"] == "Анна Петрова"  # лишние пробелы убраны

    client.post("/api/employees", json={"name": "Борис Иванов"})
    names = [e["name"] for e in client.get("/api/employees").json()["employees"]]
    assert names == ["Анна Петрова", "Борис Иванов"]


def test_duplicate_name_is_rejected_ignoring_case_and_spaces(client):
    assert client.post("/api/employees", json={"name": "Анна Петрова"}).status_code == 201
    for variant in ["анна петрова", "АННА  ПЕТРОВА", " Анна Петрова "]:
        r = client.post("/api/employees", json={"name": variant})
        assert r.status_code == 409, variant
    assert len(client.get("/api/employees").json()["employees"]) == 1


def test_blank_name_is_rejected(client):
    for bad in ["", "   "]:
        assert client.post("/api/employees", json={"name": bad}).status_code == 422
    assert client.post("/api/employees", json={"name": "x" * 101}).status_code == 422
    assert client.post("/api/employees", json={}).status_code == 422


def test_malformed_requests_get_readable_errors_not_500(client):
    r = client.post("/api/employees", content="{oops", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Проверьте поле: формат запроса"

    huge = 10**30  # не помещается в 64-битное целое SQLite
    assert client.post(f"/api/employees/{huge}/timer/stop").status_code == 422
    assert client.post(f"/api/employees/{huge}/timer/start", json={"description": "x"}).status_code == 422
    period = {"from": "2023-11-14T00:00:00Z", "to": "2023-11-15T00:00:00Z"}
    assert client.get("/api/report", params={**period, "employee_id": huge}).status_code == 422
    assert client.post("/api/employees/abc/timer/stop").status_code == 422
    assert client.post("/api/employees/0/timer/stop").status_code == 422
