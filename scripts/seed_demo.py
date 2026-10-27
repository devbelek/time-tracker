"""Заполняет БД вымышленными сотрудниками и записями за последние дни.

    python -m scripts.seed_demo

Если сотрудники уже есть, ничего не делает.
"""
import os
import time

from app import service
from app.db import connect, init_db

DB_PATH = os.environ.get("TIMETRACKER_DB", "data/timetracker.db")

EMPLOYEES = {
    "Анна Петрова": [
        ("Вёрстка главной страницы", 2 * 3600 + 15 * 60),
        ("Созвон с командой", 30 * 60),
        ("Исправление багов в форме", 1 * 3600 + 40 * 60),
    ],
    "Борис Иванов": [
        ("Проектирование API", 3 * 3600),
        ("Код-ревью", 50 * 60),
    ],
    "Виктория Сидорова": [
        ("Тестирование релиза", 2 * 3600 + 5 * 60),
        ("Написание тест-кейсов", 1 * 3600 + 20 * 60),
    ],
    "Глеб Новиков": [],  # сотрудник без записей: удобно смотреть пустой отчёт
}


def main() -> None:
    init_db(DB_PATH)
    conn = connect(DB_PATH)
    try:
        if conn.execute("SELECT 1 FROM employees LIMIT 1").fetchone():
            print("В БД уже есть сотрудники, демо-данные не добавляю.")
            return

        now = int(time.time())
        for name, tasks in EMPLOYEES.items():
            employee = service.add_employee(conn, name, now)
            # раскладываем задачи по прошлым дням, начиная с 9:00 «того» дня
            for day_back, (description, seconds) in enumerate(tasks, start=1):
                start = now - day_back * 86400 - (now % 86400) + 9 * 3600
                service.start_timer(conn, employee["id"], description, start)
                service.stop_timer(conn, employee["id"], start + seconds)
        print(f"Добавлено сотрудников: {len(EMPLOYEES)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
