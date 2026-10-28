"""Phase 8: production settings: API key gate, startup guard, Postgres URLs."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import InsecureProductionConfig, create_app

KEY = "k" * 32


def _app(**overrides: object) -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, database_url="sqlite://", **overrides)))


def test_api_key_required_when_set() -> None:
    with _app(api_key=SecretStr(KEY)) as client:
        assert client.get("/health").status_code == 200  # open for uptime checks
        res = client.get("/dashboard")
        assert res.status_code == 401
        assert res.json() == {"detail": "Missing or invalid API key."}
        assert client.get("/dashboard", headers={"X-API-Key": "wrong"}).status_code == 401
        assert client.get("/dashboard", headers={"X-API-Key": KEY}).status_code == 200


def test_no_key_means_open_for_local_development() -> None:
    with _app() as client:
        assert client.get("/dashboard").status_code == 200
        assert client.get("/docs").status_code == 200


def test_production_refuses_to_start_without_a_strong_key() -> None:
    with pytest.raises(InsecureProductionConfig):
        create_app(Settings(_env_file=None, environment="production"))
    with pytest.raises(InsecureProductionConfig):
        create_app(Settings(_env_file=None, environment="production", api_key=SecretStr("short")))


def test_production_hides_api_docs() -> None:
    with _app(environment="production", api_key=SecretStr(KEY)) as client:
        headers = {"X-API-Key": KEY}
        assert client.get("/docs", headers=headers).status_code == 404
        assert client.get("/openapi.json", headers=headers).status_code == 404


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./hiremate.db", "sqlite:///./hiremate.db"),
    ],
)
def test_database_url_gets_the_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(_env_file=None, database_url=given).database_url == expected
