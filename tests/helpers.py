"""Общие помощники для тестов API."""

from datetime import UTC, datetime

T0 = 1_700_000_000  # 2023-11-14 22:13:20 UTC, произвольная точка отсчёта


class FakeClock:
    """Управляемые часы: тесты сами решают, сколько «прошло» времени."""

    def __init__(self, now: int = T0):
        self.now = now

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += seconds


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat().replace("+00:00", "Z")


def report(client, start: int, end: int, **params):
    return client.get("/api/report", params={"from": iso(start), "to": iso(end), **params})
