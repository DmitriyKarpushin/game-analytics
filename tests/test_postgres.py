import pytest

from src.storage.postgres import build_dsn


POSTGRES_ENV = {
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "game_analytics",
    "POSTGRES_USER": "game_analytics",
    "POSTGRES_PASSWORD": "secret",
}


def test_build_dsn(monkeypatch):
    for name, value in POSTGRES_ENV.items():
        monkeypatch.setenv(name, value)

    dsn = build_dsn()

    assert "host=postgres" in dsn
    assert "port=5432" in dsn
    assert "dbname=game_analytics" in dsn
    assert "user=game_analytics" in dsn
    assert "password=secret" in dsn


def test_build_dsn_raises_when_variable_missing(monkeypatch):
    for name, value in POSTGRES_ENV.items():
        monkeypatch.setenv(name, value)

    monkeypatch.delenv("POSTGRES_PASSWORD")

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        build_dsn()
