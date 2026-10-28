"""Tests for GET /health and settings parsing."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _use_settings(**overrides: object) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, **overrides)


def test_health_reports_ok_without_key(client: TestClient) -> None:
    _use_settings(groq_api_key=None)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["llm_configured"] is False
    assert body["llm_model"] == "openai/gpt-oss-120b"


def test_health_reports_key_configured_but_never_leaks_it(client: TestClient) -> None:
    secret = "gsk_super_secret_value"
    _use_settings(groq_api_key=SecretStr(secret))
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["llm_configured"] is True
    assert secret not in res.text


def test_blank_key_counts_as_not_configured() -> None:
    assert Settings(_env_file=None, groq_api_key=SecretStr("   ")).llm_configured is False


def test_cors_origins_parsing() -> None:
    settings = Settings(_env_file=None, cors_origins=" http://localhost:3000, https://hiremate.vercel.app ,, ")
    assert settings.cors_origin_list == ["http://localhost:3000", "https://hiremate.vercel.app"]
