"""Phase 7: dashboard summary."""

import json
from datetime import date
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.services.dashboard_service import score_history, skill_gaps, stats, upcoming_deadlines
from tests.conftest import use_fake_llm

# The analyze endpoint needs at least 80 characters of posting text.
POSTING = "Nimbus Analytics is hiring a Backend Intern in Lahore. You will build APIs in Python and ship them with Docker."


def card(id: int, status: str, deadline: date | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=id, status=status, deadline=deadline, title=f"Role {id}", company="Acme")


def job(score: int | None, missing: list[str] | None = None, documents: list | None = None) -> SimpleNamespace:
    result = {"missing_required": missing or []} if score is not None else None
    return SimpleNamespace(match_score=score, match_result=result, documents=documents or [])


def test_stats_and_interview_rate() -> None:
    cards = [card(1, "saved"), card(2, "applied"), card(3, "interview"), card(4, "offer"), card(5, "rejected")]
    jobs = [job(80, documents=["doc"]), job(60), job(None)]
    result = stats(cards, jobs)  # type: ignore[arg-type]
    assert (result.applications, result.active, result.sent, result.interviews, result.offers) == (5, 3, 4, 2, 1)
    assert result.interview_rate == 50
    assert (result.jobs_analyzed, result.jobs_scored, result.average_match, result.documents_ready) == (3, 2, 70, 1)
    empty = stats([], [])
    assert empty.interview_rate is None and empty.average_match is None


def test_deadlines_window_skips_closed_and_sorts() -> None:
    today = date(2026, 10, 28)
    cards = [
        card(1, "applied", date(2026, 11, 5)),
        card(2, "saved", date(2026, 10, 20)),  # overdue: still shown
        card(3, "offer", date(2026, 10, 30)),  # closed: hidden
        card(4, "saved", date(2026, 12, 25)),  # too far away
        card(5, "interview"),  # no deadline
    ]
    assert [d.application_id for d in upcoming_deadlines(cards, today)] == [2, 1]  # type: ignore[arg-type]


def test_skill_gaps_count_once_per_job_case_insensitively() -> None:
    jobs = [job(50, ["Docker", "AWS", "docker"]), job(40, ["docker", "Kubernetes"]), job(None)]
    gaps = skill_gaps(jobs)  # type: ignore[arg-type]
    assert [(g.skill, g.jobs) for g in gaps] == [("Docker", 2), ("AWS", 1), ("Kubernetes", 1)]


def test_score_history_is_oldest_first_and_skips_unscored() -> None:
    from datetime import datetime, timezone

    def scored(id: int, score: int | None) -> SimpleNamespace:
        return SimpleNamespace(id=id, title=f"Job {id}", company="", match_score=score, created_at=datetime(2026, 10, id, tzinfo=timezone.utc))

    jobs = [scored(3, 70), scored(2, None), scored(1, 55)]  # newest first, like the query
    assert [(p.job_id, p.score) for p in score_history(jobs)] == [(1, 55), (3, 70)]  # type: ignore[arg-type]


def test_dashboard_endpoint(client: TestClient) -> None:
    empty = client.get("/dashboard").json()
    assert empty["has_profile"] is False
    assert [s["count"] for s in empty["pipeline"]] == [0, 0, 0, 0, 0]
    assert empty["stats"]["interview_rate"] is None

    client.put("/profile", json={"full_name": "Sara Ahmed", "skills": ["Python"]})
    use_fake_llm(json.dumps({"title": "Backend Intern", "company": "Nimbus", "required_skills": ["Python", "Docker"]}))
    job_id = client.post("/jobs/analyze", json={"text": POSTING}).json()["id"]
    card_id = client.post("/applications", json={"job_id": job_id, "deadline": date.today().isoformat()}).json()["id"]
    client.post(f"/applications/{card_id}/move", json={"status": "applied"})

    data = client.get("/dashboard").json()
    assert data["profile_name"] == "Sara Ahmed" and data["has_profile"] is True
    assert data["stats"]["applications"] == 1 and data["stats"]["sent"] == 1
    assert data["pipeline"][1] == {"status": "applied", "label": "Applied", "count": 1}
    assert data["deadlines"][0]["application_id"] == card_id
    assert data["recent_jobs"][0]["application_status"] == "applied"
    assert data["activity"][0]["message"] == "Moved from Saved to Applied"
    assert data["score_history"] == []  # analyzed but not scored yet
    assert {item["kind"] for item in data["activity"]} >= {"analyzed", "status", "created"}
