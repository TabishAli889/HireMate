"""Profile endpoints end-to-end with a fake LLM."""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.llm import get_llm_provider
from tests.conftest import FakeProvider, make_pdf

PARSED = {
    "full_name": "Sara Ahmed",
    "skills": ["Python", "FastAPI"],
    "experience": [{"company": "Acme", "title": "Intern", "bullets": ["Built an API"]}],
    "projects": [{"name": "Chatbot", "tech_stack": ["LangChain"]}],
}
PDF = make_pdf("Sara Ahmed - Python developer - FastAPI - Acme intern - built an API")


def _use_fake_llm(*replies: str) -> FakeProvider:
    provider = FakeProvider(list(replies))
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return provider


def _upload(client: TestClient, content: bytes = PDF, name: str = "cv.pdf"):
    return client.post("/profile/upload", files={"file": (name, content, "application/pdf")})


def test_get_profile_404_when_empty(client: TestClient) -> None:
    res = client.get("/profile")
    assert res.status_code == 404
    assert "Upload" in res.json()["detail"]


def test_upload_creates_profile(client: TestClient) -> None:
    provider = _use_fake_llm(json.dumps(PARSED))
    res = _upload(client)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["full_name"] == "Sara Ahmed"
    assert body["experience"][0]["bullets"] == ["Built an API"]
    assert body["source_filename"] == "cv.pdf"
    assert body["is_demo"] is False
    assert "FastAPI" in provider.calls[0][1]["content"]  # resume text reached the LLM
    assert client.get("/profile").json()["projects"][0]["name"] == "Chatbot"


def test_put_replaces_profile_and_children(client: TestClient) -> None:
    _use_fake_llm(json.dumps(PARSED))
    _upload(client)
    edited = {**PARSED, "skills": ["Python"], "experience": [], "projects": [{"name": "New", "bullets": ["x"]}]}
    res = client.put("/profile", json=edited)
    assert res.status_code == 200
    body = client.get("/profile").json()
    assert body["skills"] == ["Python"]
    assert body["experience"] == []
    assert [p["name"] for p in body["projects"]] == ["New"]


def test_put_rejects_invalid_body(client: TestClient) -> None:
    assert client.put("/profile", json={"skills": "Python"}).status_code == 422


def test_non_pdf_upload_rejected(client: TestClient) -> None:
    _use_fake_llm()
    res = _upload(client, b"hello", "cv.txt")
    assert res.status_code == 422
    assert "PDF" in res.json()["detail"]


def test_upload_without_api_key_is_friendly_503(client: TestClient) -> None:
    res = _upload(client)
    assert res.status_code == 503
    assert "GROQ_API_KEY" in res.json()["detail"]


def test_llm_garbage_gives_502_after_retries(client: TestClient) -> None:
    provider = _use_fake_llm("bad", "bad", "bad")
    res = _upload(client)
    assert res.status_code == 502
    assert len(provider.calls) == 3
    assert client.get("/profile").status_code == 404  # nothing half-saved


def test_upload_is_rate_limited(client: TestClient) -> None:
    _use_fake_llm(*[json.dumps(PARSED)] * 10)
    statuses = [_upload(client).status_code for _ in range(6)]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429
