"""Чистая логика без БД и HTTP: быстрые юнит-тесты и проверки свойств (hypothesis)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.db import connect, migrate
from app.domain import InvalidPeriod, Period, name_key, normalize_name, overlap_seconds
from app.repository import Repository
from app.service import TimeTracker

# ---------- имена ----------


def test_normalize_name_collapses_whitespace():
    assert normalize_name("  Анна \t  Петрова \n") == "Анна Петрова"


@pytest.mark.parametrize("variant", ["анна петрова", "АННА ПЕТРОВА", "  Анна   Петрова "])
def test_name_key_treats_cyrillic_case_and_spaces_as_same_person(variant):
    assert name_key(variant) == name_key("Анна Петрова")


def test_name_key_distinguishes_different_people():
    assert name_key("Анна Петрова") != name_key("Анна Петров")


# ---------- пересечение записи с окном ----------


@pytest.mark.parametrize(
    ("start", "stop", "window", "now", "expected"),
    [
        (100, 200, (0, 1000), 500, 100),  # запись целиком внутри окна
        (100, 200, (150, 1000), 500, 50),  # запись начата до окна
        (100, 200, (0, 150), 500, 50),  # запись заканчивается после окна
        (100, 200, (120, 130), 500, 10),  # окно целиком внутри записи
        (100, 200, (200, 300), 500, 0),  # окно начинается ровно в конце записи
        (100, 200, (0, 100), 500, 0),  # окно заканчивается ровно в начале записи
        (100, None, (0, 1000), 400, 300),  # идущий таймер: считаем до now
        (100, None, (0, 250), 400, 150),  # идущий таймер, окно закончилось раньше now
        (100, 100, (0, 1000), 500, 0),  # запись нулевой длины
    ],
)
def test_overlap_seconds(start, stop, window, now, expected):
    assert overlap_seconds(start, stop, window[0], window[1], now) == expected


# ---------- период ----------


@pytest.mark.parametrize("start", range(3))
def test_period_rejects_empty_and_reversed(start):
    with pytest.raises(InvalidPeriod):
        Period(start + 10, start + 10)
    with pytest.raises(InvalidPeriod):
        Period(start + 10, start)


def test_period_rejects_out_of_range_dates():
    with pytest.raises(InvalidPeriod):
        Period(-1, 100)
    with pytest.raises(InvalidPeriod):
        Period(0, 4_102_444_801)


# ---------- свойства ----------

ts = st.integers(min_value=0, max_value=10_000)


@given(start=ts, length=st.integers(0, 5_000), w1=ts, w2=ts, now=ts)
def test_overlap_never_exceeds_entry_or_window(start, length, w1, w2, now):
    lo, hi = sorted((w1, w2))
    got = overlap_seconds(start, start + length, lo, hi, now)
    assert 0 <= got <= min(length, hi - lo)


@given(start=ts, length=st.integers(0, 5_000), a=ts, b=ts, c=ts, now=ts)
def test_overlap_is_additive_over_adjacent_windows(start, length, a, b, c, now):
    """Если разрезать окно на две части, сумма по частям равна значению по целому окну."""
    a, b, c = sorted((a, b, c))
    whole = overlap_seconds(start, start + length, a, c, now)
    parts = overlap_seconds(start, start + length, a, b, now) + overlap_seconds(start, start + length, b, c, now)
    assert whole == parts


@given(
    entries=st.lists(
        st.tuples(st.integers(0, 5_000), st.integers(0, 2_000), st.booleans()),
        max_size=8,
    ),
    cuts=st.lists(st.integers(0, 8_000), min_size=3, max_size=3, unique=True),
    now=st.integers(5_000, 9_000),
)
def test_report_total_is_additive_through_the_whole_stack(entries, cuts, now):
    """Сквозная проверка: отчёт за [a, c) равен сумме отчётов за [a, b) и [b, c).

    Это ловит ошибки на границах периода: потерянные или посчитанные дважды секунды.
    """
    conn = connect(":memory:")
    migrate(conn)
    repo = Repository(conn)
    tracker = TimeTracker(repo, clock=lambda: now)
    employee = repo.add_employee("Анна Петрова", name_key("Анна Петрова"), 0)

    last_stop = 0
    for index, (gap, length, keep_running) in enumerate(entries):
        start = last_stop + gap
        if start >= now:
            break
        repo.start_entry(employee.id, f"Задача {index}", start)
        if keep_running and index == len(entries) - 1:
            break  # последняя запись остаётся идущим таймером
        last_stop = start + length
        repo.stop_running_entry(employee.id, last_stop)

    a, b, c = sorted(cuts)
    whole = tracker.report(a, c).total_seconds
    parts = tracker.report(a, b).total_seconds + tracker.report(b, c).total_seconds
    assert whole == parts
    conn.close()
