"""Регрессия: на живом сервере запросы падали с 500 из-за переноса соединения между потоками."""
import threading
from concurrent.futures import ThreadPoolExecutor

from app.db import connect, init_db
from conftest import T0, report


def test_connection_can_be_used_from_another_thread(db_path):
    init_db(db_path)
    conn = connect(db_path)  # создано в одном потоке...
    result = []
    worker = threading.Thread(target=lambda: result.append(conn.execute("SELECT 1").fetchone()[0]))
    worker.start()  # ...а используется в другом, как делает FastAPI
    worker.join()
    assert result == [1]
    conn.close()


def test_many_parallel_requests_do_not_fail(client, anna):
    """Дымовая проверка. Сам баг она не воспроизводит (TestClient ходит иначе, чем uvicorn),
    это делает тест выше; здесь только убеждаемся, что параллельные запросы не ломают друг друга."""

    def call(i):
        if i % 2:
            return client.get("/api/employees").status_code
        return report(client, T0 - 60, T0 + 60).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(call, range(60)))
    assert set(codes) == {200}
