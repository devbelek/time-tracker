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


def test_large_static_files_are_gzipped(client):
    r = client.get("/vendor/bootstrap/bootstrap.min.css", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip"
    assert r.headers["content-type"].startswith("text/css")
    assert r.headers["content-security-policy"]  # заголовки безопасности не потерялись из-за сжатия


def test_small_api_responses_are_not_compressed(client):
    r = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in r.headers


def test_fonts_are_served_with_font_mime_type(client):
    r = client.get("/vendor/fonts/ibm-plex-sans/ibm-plex-sans-cyrillic-400-normal.woff2")
    assert r.status_code == 200
    assert r.headers["content-type"] == "font/woff2"
