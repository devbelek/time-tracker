PY := .venv/bin/python
PIP := .venv/bin/pip

.DEFAULT_GOAL := help
.PHONY: help install install-e2e run seed test lint format types js-test e2e check docker

help: ## Список команд
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

.venv:
	python3 -m venv .venv

install: .venv ## Установить зависимости для разработки
	$(PIP) install -r requirements-dev.txt

install-e2e: install ## Дополнительно: Playwright и Chromium для сквозных тестов
	$(PIP) install -r requirements-e2e.txt
	.venv/bin/playwright install chromium

run: ## Запустить приложение на http://localhost:8000
	$(PY) -m uvicorn app.main:create_app --factory --port 8000

seed: ## Добавить вымышленные демо-данные
	$(PY) -m scripts.seed_demo

test: ## Тесты Python с покрытием (быстро, браузер не нужен)
	$(PY) -m pytest

lint: ## Линтер и проверка форматирования
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format: ## Автоформатирование и автоисправление линтера
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

types: ## Проверка типов (mypy, строгий режим)
	.venv/bin/mypy

js-test: ## Тесты фронтенда (node --test, без зависимостей)
	npm test

e2e: ## Сквозные тесты в настоящем браузере
	$(PY) -m pytest -m e2e --no-cov

check: lint types test js-test ## Всё, что запускается в CI, кроме браузерных тестов

docker: ## Собрать образ и запустить на http://localhost:8000
	docker compose up --build
