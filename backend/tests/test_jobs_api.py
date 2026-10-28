"""Job endpoints end-to-end with a fake LLM."""

import json

import pytest
from fastapi.testclient import TestClient

from app.services import job_scraper
from app.services.matching import compute_score
from tests.conftest import use_fake_llm

POSTING = (
    "Nimbus Analytics is hiring a Backend Intern in Lahore. You will build REST APIs in Python, "
    "write SQL queries and ship services with Docker. AWS experience is a plus."
)
EXTRACTED = json.dumps(
    {
        "title": "Backend Intern",
        "company": "Nimbus Analytics",
        "location": "Lahore",
        "seniority": "internship",
        "required_skills": ["Python", "SQL", "REST APIs", "Docker"],
        "nice_to_have_skills": ["AWS"],
        "responsibilities": ["Build REST APIs", "Write SQL queries"],
        "summary": "A backend internship building APIs.",
    }
)
PROFILE = {
    "full_name": "Sara",
    "skills": ["Python", "PostgreSQL"],
    "projects": [{"name": "Bot", "bullets": ["Built REST APIs with FastAPI"]}],
}
SEMANTIC = json.dumps({"matches": [{"skill": "SQL", "evidence_quote": "PostgreSQL"}]})
EXPLANATION = json.dumps({"explanation": "Solid fit: you show Python, REST APIs and SQL. Docker is the main gap."})
PLAN = json.dumps(
    {"gap_plan": [{"skill": "Docker", "why": "They ship with it.", "first_steps": ["Dockerise Bot"], "estimated_time": "1 week"}]}
)


def _analyze(client: TestClient, **body: str):
    return client.post("/jobs/analyze", json=body)


def test_analyze_text_creates_job(client: TestClient) -> None:
    use_fake_llm(EXTRACTED)
    res = _analyze(client, text=POSTING)
    assert res.status_code == 200, res.text
    job = res.json()
    assert job["title"] == "Backend Intern"
    assert job["required_skills"] == ["Python", "SQL", "REST APIs", "Docker"]
    assert job["match"] is None
    assert job["created_at"].endswith(("Z", "+00:00"))
    assert client.get(f"/jobs/{job['id']}").json()["company"] == "Nimbus Analytics"
    assert client.get("/jobs").json()[0]["id"] == job["id"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({}, "either"),
        ({"text": POSTING, "url": "https://example.com/job"}, "either"),
        ({"text": "Hiring now"}, "too short"),
    ],
)
def test_analyze_validates_input(client: TestClient, body: dict, message: str) -> None:
    use_fake_llm()
    res = client.post("/jobs/analyze", json=body)
    assert res.status_code == 422
    assert message in res.json()["detail"]


def test_analyze_url_uses_scraper(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job_scraper, "scrape_job_url", lambda url: POSTING)
    use_fake_llm(EXTRACTED)
    res = _analyze(client, url="https://careers.example.com/backend-intern")
    assert res.status_code == 200
    assert res.json()["source_url"] == "https://careers.example.com/backend-intern"


def test_scrape_failure_tells_user_to_paste(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(url: str) -> str:
        raise job_scraper.ScrapeError()

    monkeypatch.setattr(job_scraper, "scrape_job_url", blocked)
    use_fake_llm()
    res = _analyze(client, url="https://www.linkedin.com/jobs/view/1")
    assert res.status_code == 422
    assert "paste" in res.json()["detail"]


def test_non_job_text_is_rejected(client: TestClient) -> None:
    use_fake_llm(json.dumps({}))
    res = _analyze(client, text="This is a recipe for chicken karahi. " * 5)
    assert res.status_code == 422
    assert "job posting" in res.json()["detail"]


def test_match_requires_profile(client: TestClient) -> None:
    use_fake_llm(EXTRACTED)
    job_id = _analyze(client, text=POSTING).json()["id"]
    res = client.post(f"/jobs/{job_id}/match")
    assert res.status_code == 409


def test_match_scores_and_stores_result(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    use_fake_llm(EXTRACTED, SEMANTIC, EXPLANATION, PLAN)
    job_id = _analyze(client, text=POSTING).json()["id"]

    res = client.post(f"/jobs/{job_id}/match")
    assert res.status_code == 200, res.text
    match = res.json()
    assert match["score"] == compute_score(4, 3, 1, 0, "internship")[0]
    assert {m["skill"] for m in match["matched_skills"]} == {"Python", "REST APIs", "SQL"}
    assert match["missing_required"] == ["Docker"]
    assert match["gap_plan"][0]["skill"] == "Docker"

    stored = client.get(f"/jobs/{job_id}").json()
    assert stored["match"]["score"] == match["score"]
    assert client.get("/jobs").json()[0]["match_score"] == match["score"]


def test_unknown_job_is_404(client: TestClient) -> None:
    assert client.get("/jobs/999").status_code == 404
    use_fake_llm()
    client.put("/profile", json=PROFILE)
    assert client.post("/jobs/999/match").status_code == 404


def test_same_posting_reuses_requirements_and_score(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = use_fake_llm(EXTRACTED, SEMANTIC, EXPLANATION, PLAN)
    first = _analyze(client, text=POSTING).json()
    score = client.post(f"/jobs/{first['id']}/match").json()["score"]
    calls_after_first_run = len(provider.calls)

    second = _analyze(client, text=POSTING).json()  # same text: no new job, no extraction call
    assert second["id"] == first["id"]
    again = client.post(f"/jobs/{second['id']}/match").json()  # same profile: score kept, no AI calls
    assert again["score"] == score
    assert len(provider.calls) == calls_after_first_run
    assert len(client.get("/jobs").json()) == 1


def test_profile_change_triggers_rescore(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = use_fake_llm(EXTRACTED, SEMANTIC, EXPLANATION, PLAN)
    job_id = _analyze(client, text=POSTING).json()["id"]
    before = client.post(f"/jobs/{job_id}/match").json()
    assert "Docker" in before["missing_required"]

    client.put("/profile", json={**PROFILE, "skills": [*PROFILE["skills"], "Docker"]})
    provider.replies += [SEMANTIC, json.dumps({"explanation": "Now you cover every required skill for this role."}), PLAN]
    after = client.post(f"/jobs/{job_id}/match").json()
    assert after["missing_required"] == []
    assert after["score"] > before["score"]
