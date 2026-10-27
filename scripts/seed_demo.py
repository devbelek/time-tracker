"""Заполняет БД вымышленными сотрудниками и записями за последние дни.

    python -m scripts.seed_demo

Если сотрудники уже есть, ничего не делает.
"""

import time

from app.config import Settings
from app.db import connect, init_db
from app.domain import name_key
from app.repository import Repository

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
    db_path = Settings.from_env().db_path
    init_db(db_path)
    conn = connect(db_path)
    try:
        repo = Repository(conn)
        if repo.list_employees():
            print("В БД уже есть сотрудники, демо-данные не добавляю.")
            return

        now = int(time.time())
        for name, tasks in EMPLOYEES.items():
            employee = repo.add_employee(name, name_key(name), now)
            # раскладываем задачи по прошлым дням, начиная с 9:00 «того» дня
            for day_back, (description, seconds) in enumerate(tasks, start=1):
                start = now - day_back * 86400 - (now % 86400) + 9 * 3600
                repo.start_entry(employee.id, description, start)
                repo.stop_running_entry(employee.id, start + seconds)
        print(f"Добавлено сотрудников: {len(EMPLOYEES)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
