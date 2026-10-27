"""Сценарии пользователя в браузере."""

import pytest
from playwright.sync_api import Locator, Page, expect

from app.domain import name_key

pytestmark = pytest.mark.e2e


# ---------- помощники ----------


def add_employee(page: Page, name: str) -> None:
    page.get_by_label("Имя сотрудника").fill(name)
    page.get_by_role("button", name="Добавить").click()


def card(page: Page, name: str) -> Locator:
    return page.locator("#employees li", has_text=name)


def start_timer(page: Page, name: str, task: str) -> None:
    row = card(page, name)
    row.get_by_placeholder("Над чем работаете?").fill(task)
    row.get_by_role("button", name="Старт").click()


# ---------- основной сценарий ----------


def test_empty_state_before_any_employee(page: Page):
    expect(page.locator("#employees")).to_contain_text("Пока никого нет")
    expect(page.locator("#report")).to_contain_text("Сотрудников пока нет")


def test_add_employee_start_and_stop_timer_then_see_it_in_report(page: Page):
    add_employee(page, "Анна Петрова")
    expect(page.locator("#message")).to_contain_text("Добавлен: Анна Петрова")

    start_timer(page, "Анна Петрова", "Вёрстка главной")
    anna = card(page, "Анна Петрова")
    expect(anna).to_contain_text("Идёт")
    expect(anna).to_contain_text("Вёрстка главной")
    # счётчик тикает
    expect(anna.locator(".timer")).not_to_have_text("0:00:00", timeout=5000)

    anna.get_by_role("button", name="Остановить").click()
    expect(page.locator("#message")).to_contain_text("Остановлено: «Вёрстка главной»")
    expect(anna).not_to_contain_text("Идёт")

    # отчёт за сегодня обновился сам
    page.locator("#report summary", has_text="Анна Петрова").click()
    expect(page.locator("#report")).to_contain_text("Вёрстка главной")
    expect(page.locator("#report")).to_contain_text("1 запись")


def test_empty_report_for_period_without_entries(page: Page):
    add_employee(page, "Анна Петрова")
    expect(card(page, "Анна Петрова")).to_be_visible()

    expect(page.locator("#report")).to_contain_text("За выбранный период записей нет.")
    expect(page.locator("#report")).to_contain_text("0:00:00")


def test_entry_with_zero_duration_is_not_reported_as_missing(page: Page):
    """Старт и мгновенный стоп: запись есть, хотя суммарное время нулевое."""
    add_employee(page, "Анна Петрова")
    start_timer(page, "Анна Петрова", "Быстрая задача")
    card(page, "Анна Петрова").get_by_role("button", name="Остановить").click()

    report = page.locator("#report")
    expect(report).to_contain_text("считается только время внутри периода")
    expect(report).not_to_contain_text("записей нет")


def test_repeated_start_from_a_stale_tab_shows_error_and_current_state(page: Page, server):
    add_employee(page, "Анна Петрова")
    expect(card(page, "Анна Петрова")).to_be_visible()

    stale = page.context.new_page()  # вторая вкладка, увидит сотрудника свободным
    stale.goto(server.url)
    expect(card(stale, "Анна Петрова").get_by_role("button", name="Старт")).to_be_visible()

    start_timer(page, "Анна Петрова", "Первая задача")
    expect(card(page, "Анна Петрова")).to_contain_text("Идёт")

    start_timer(stale, "Анна Петрова", "Вторая задача")
    expect(stale.locator("#message")).to_contain_text("Таймер уже запущен")
    expect(card(stale, "Анна Петрова")).to_contain_text("Первая задача")  # вкладка догнала реальное состояние


def test_start_without_description_is_blocked(page: Page):
    add_employee(page, "Анна Петрова")
    card(page, "Анна Петрова").get_by_role("button", name="Старт").click()
    expect(page.locator("#message")).to_contain_text("Опишите задачу")
    expect(card(page, "Анна Петрова")).not_to_contain_text("Идёт")


def test_duplicate_employee_is_rejected_with_message(page: Page):
    add_employee(page, "Анна Петрова")
    expect(card(page, "Анна Петрова")).to_be_visible()
    add_employee(page, "  анна   ПЕТРОВА ")
    expect(page.locator("#message")).to_contain_text("уже добавлен")
    expect(page.locator("#employees li")).to_have_count(1)


# ---------- сохранение данных ----------


def test_data_and_running_timer_survive_server_restart(page: Page, server):
    add_employee(page, "Анна Петрова")
    start_timer(page, "Анна Петрова", "Долгая задача")
    expect(card(page, "Анна Петрова")).to_contain_text("Идёт")

    server.restart()
    page.reload()

    anna = card(page, "Анна Петрова")
    expect(anna).to_contain_text("Долгая задача")
    expect(anna).to_contain_text("Идёт")


# ---------- отчёт и часовые пояса ----------


def test_report_splits_entry_at_local_midnight(page: Page, server):
    """Запись 23:00-01:00 по Бишкеку (UTC+6) делится по местной полуночи: по часу на каждый день."""
    key = name_key("Борис Иванов")

    def fill(repo):
        boris = repo.add_employee("Борис Иванов", key, 0)
        # 2026-03-09 23:00 +06 = 17:00 UTC, 2026-03-10 01:00 +06 = 19:00 UTC
        start = 1_773_075_600  # 2026-03-09T17:00:00Z
        repo.start_entry(boris.id, "Ночной релиз", start)
        repo.stop_running_entry(boris.id, start + 2 * 3600)

    server.seed(fill)
    page.reload()

    for day in ("2026-03-09", "2026-03-10"):
        page.locator("#from").fill(day)
        page.locator("#to").fill(day)
        page.get_by_role("button", name="Показать").click()
        row = page.locator("#report tbody tr", has_text="Борис Иванов")
        expect(row).to_contain_text("1:00:00")

    page.locator("#to").fill("2026-03-10")
    page.locator("#from").fill("2026-03-09")
    page.get_by_role("button", name="Показать").click()
    expect(page.locator("#report tbody tr", has_text="Борис Иванов")).to_contain_text("2:00:00")


def test_report_filter_by_employee(page: Page):
    add_employee(page, "Анна Петрова")
    add_employee(page, "Борис Иванов")
    expect(card(page, "Борис Иванов")).to_be_visible()

    page.get_by_label("Сотрудник", exact=True).select_option(label="Борис Иванов")
    expect(page.locator("#report tbody tr")).to_have_count(1)
    expect(page.locator("#report tbody")).to_contain_text("Борис Иванов")


def test_invalid_period_shows_server_message(page: Page):
    add_employee(page, "Анна Петрова")
    page.locator("#from").fill("2026-03-10")
    page.locator("#to").fill("2026-03-01")
    page.get_by_role("button", name="Показать").click()
    expect(page.locator("#message")).to_contain_text("Начало периода должно быть раньше")


# ---------- интерфейс ----------


def test_draft_task_text_survives_adding_another_employee(page: Page):
    add_employee(page, "Борис Иванов")
    card(page, "Борис Иванов").get_by_placeholder("Над чем работаете?").fill("Недописанный черновик")
    add_employee(page, "Виктория Сидорова")
    expect(card(page, "Виктория Сидорова")).to_be_visible()
    expect(card(page, "Борис Иванов").get_by_placeholder("Над чем работаете?")).to_have_value("Недописанный черновик")


def test_typing_next_name_while_previous_request_is_in_flight_is_not_erased(page: Page):
    """Гонка: ответ на «Добавить» не должен стирать имя, которое пользователь уже начал вводить следующим.

    Ответ сервера удерживается через перехват запроса, поэтому тест не зависит от скорости сети.
    """
    held = []

    def hold_post(route):
        if route.request.method == "POST":
            held.append(route)  # запрос «висит», пока тест его не отпустит
        else:
            route.continue_()

    page.route("**/api/employees", hold_post)
    name_input = page.get_by_label("Имя сотрудника")
    name_input.fill("Анна Петрова")
    page.get_by_role("button", name="Добавить").click()
    while not held:
        page.wait_for_timeout(20)

    name_input.fill("Борис Иванов")  # пользователь уже печатает следующее имя
    held[0].continue_()  # и только теперь приходит ответ на первый запрос

    expect(card(page, "Анна Петрова")).to_be_visible()
    expect(name_input).to_have_value("Борис Иванов")


def test_html_in_names_is_shown_as_text_not_executed(page: Page):
    evil = '<img src=x onerror="window.__xss=1"><b>Хакер</b>'
    add_employee(page, evil)
    expect(page.locator("#employees")).to_contain_text(evil)
    assert page.locator("#employees img, #employees b").count() == 0
    assert page.evaluate("window.__xss") is None


def test_theme_toggle_switches_and_is_remembered(page: Page):
    html = page.locator("html")
    expect(html).to_have_attribute("data-bs-theme", "light")
    page.locator("#theme-toggle").click()
    expect(html).to_have_attribute("data-bs-theme", "dark")
    page.reload()
    expect(html).to_have_attribute("data-bs-theme", "dark")


def test_happy_path_has_no_console_errors_or_csp_violations(page: Page):
    add_employee(page, "Анна Петрова")
    start_timer(page, "Анна Петрова", "Задача")
    expect(card(page, "Анна Петрова")).to_contain_text("Идёт")
    card(page, "Анна Петрова").get_by_role("button", name="Остановить").click()
    expect(page.locator("#message")).to_contain_text("Остановлено")
    page.locator("[data-range=month]").click()
    page.wait_for_load_state("networkidle")
    assert page.errors == []  # type: ignore[attr-defined]


def test_layout_fits_phone_width_without_horizontal_scroll(page: Page):
    add_employee(page, "Анна Петрова")
    page.set_viewport_size({"width": 375, "height": 800})
    expect(card(page, "Анна Петрова")).to_be_visible()
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert overflow is False
