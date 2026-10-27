"""Служебные свойства приложения: health, заголовки безопасности, раздача фронтенда."""

import sqlite3

from app.db import MIGRATIONS


def test_health_reports_ok_and_schema_version(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "schema_version": len(MIGRATIONS)}


def test_health_returns_503_when_database_is_unavailable(client, monkeypatch):
    def broken(_path):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr("app.main.connect", broken)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "unavailable"}


def test_frontend_is_served_with_strict_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Учёт рабочего времени" in r.text
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert r.headers["x-content-type-options"] == "nosniff"


def test_swagger_docs_are_not_blocked_by_csp(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "content-security-policy" not in r.headers  # Swagger UI грузит скрипты с CDN


def test_api_responses_are_not_cached(client):
    assert client.get("/api/employees").headers["cache-control"] == "no-store"


def test_openapi_schema_is_available(client):
    schema = client.get("/openapi.json").json()
    assert "/api/report" in schema["paths"]


def test_settings_are_read_from_environment(monkeypatch, tmp_path):
    from app.config import Settings

    monkeypatch.setenv("TIMETRACKER_DB", str(tmp_path / "custom.db"))
    monkeypatch.setenv("TIMETRACKER_LOG_LEVEL", "debug")
    settings = Settings.from_env()
    assert settings.db_path == tmp_path / "custom.db"
    assert settings.log_level == "DEBUG"


def test_settings_have_sensible_defaults(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("TIMETRACKER_DB", raising=False)
    monkeypatch.delenv("TIMETRACKER_LOG_LEVEL", raising=False)
    assert Settings.from_env() == Settings()
