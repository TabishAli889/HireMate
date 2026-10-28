"""Phase 5 endpoints end-to-end with a fake LLM."""

import json

from fastapi.testclient import TestClient

from tests.conftest import use_fake_llm

POSTING = (
    "Nimbus Analytics is hiring a Backend Intern in Lahore. You will build REST APIs in Python, "
    "write SQL queries and ship services with Docker. AWS experience is a plus."
)
EXTRACTED = json.dumps(
    {
        "title": "Backend Intern",
        "company": "Nimbus Analytics",
        "seniority": "internship",
        "required_skills": ["Python", "REST APIs", "Docker"],
        "nice_to_have_skills": ["AWS"],
    }
)
PROFILE = {
    "full_name": "Sara Ahmed",
    "skills": ["Python", "FastAPI"],
    "projects": [{"name": "Bot", "bullets": ["Built REST APIs with FastAPI", "Wrote tests"]}],
}
EXPLANATION = json.dumps({"explanation": "Good fit: Python and REST APIs. Docker is the gap."})
TAILOR = json.dumps(
    {
        "bullets": [
            {"id": "proj0-b0", "rewritten": "Designed and built REST APIs in Python with FastAPI", "reason": "REST APIs"},
            {"id": "proj0-b1", "rewritten": "Containerised the API with Docker", "reason": "Docker"},  # claims missing skill
        ],
        "project_ranking": [{"name": "Bot", "reason": "Closest to the role"}],
    }
)
LETTER = json.dumps(
    {"paragraphs": ["I'm excited to apply for the Backend Intern role.", "In my Bot project I built REST APIs with FastAPI.", "I'd love to talk."]}
)
QUESTIONS = json.dumps(
    {
        "questions": [
            {"question": f"Question {i}?", "category": "technical", "hint": "Talk about Bot.", "project": "bot" if i == 0 else "Ghost"}
            for i in range(8)
        ]
    }
)


def _job(client: TestClient, *replies: str) -> tuple[int, object]:
    client.put("/profile", json=PROFILE)
    provider = use_fake_llm(EXTRACTED, *replies)
    job_id = client.post("/jobs/analyze", json={"text": POSTING}).json()["id"]
    return job_id, provider


def test_tailor_scores_first_then_guards_and_reuses(client: TestClient) -> None:
    # No match yet: tailoring scores first (semantic + explanation), then tailors.
    job_id, provider = _job(client, json.dumps({"matches": []}), EXPLANATION, TAILOR)
    res = client.post(f"/jobs/{job_id}/tailor")
    assert res.status_code == 200, res.text
    bullets = {b["id"]: b for b in res.json()["bullets"]}
    assert bullets["proj0-b0"]["tailored"].startswith("Designed and built")
    assert bullets["proj0-b0"]["status"] == "pending"
    assert bullets["proj0-b1"]["tailored"] == "Wrote tests"
    assert "Docker" in bullets["proj0-b1"]["guard_note"]

    calls = len(provider.calls)
    again = client.post(f"/jobs/{job_id}/tailor").json()
    assert again["generated_at"] == res.json()["generated_at"]
    assert len(provider.calls) == calls  # same profile: reused, no AI call

    job = client.get(f"/jobs/{job_id}").json()
    assert job["tailoring"]["bullets"][0]["id"] == "proj0-b0"
    assert client.get("/jobs").json()[0]["has_tailoring"] is True


def test_accept_reject_and_pdf_export(client: TestClient) -> None:
    job_id, _ = _job(client, json.dumps({"matches": []}), EXPLANATION, TAILOR)
    client.post(f"/jobs/{job_id}/tailor")

    res = client.patch(f"/jobs/{job_id}/tailor", json={"decisions": {"proj0-b0": "accepted"}})
    assert res.status_code == 200
    assert res.json()["bullets"][0]["status"] == "accepted"
    assert client.patch(f"/jobs/{job_id}/tailor", json={"decisions": {"nope": "accepted"}}).status_code == 422

    edited = client.patch(f"/jobs/{job_id}/tailor", json={"edits": {"proj0-b1": "Wrote 40 unit tests with pytest"}}).json()
    mine = next(b for b in edited["bullets"] if b["id"] == "proj0-b1")
    assert mine["tailored"] == "Wrote 40 unit tests with pytest"  # the user's own numbers are trusted
    assert mine["status"] == "accepted" and mine["guard_note"] == ""

    pdf = client.get(f"/jobs/{job_id}/tailor/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF")


def test_pdf_before_tailoring_is_404(client: TestClient) -> None:
    job_id, _ = _job(client)
    assert client.get(f"/jobs/{job_id}/tailor/pdf").status_code == 404


def test_cover_letter_generate_edit_and_export(client: TestClient) -> None:
    job_id, provider = _job(client, json.dumps({"matches": []}), EXPLANATION, LETTER)
    res = client.post(f"/jobs/{job_id}/cover-letter", json={"tone": "friendly"})
    assert res.status_code == 200, res.text
    letter = res.json()
    assert letter["tone"] == "friendly"
    assert letter["body"].startswith("Dear Hiring Team at Nimbus Analytics,")
    assert letter["body"].endswith("Sincerely,\nSara Ahmed")
    assert letter["warnings"] == []

    edited = client.put(
        f"/jobs/{job_id}/cover-letter/friendly", json={"body": letter["body"] + "\n\nP.S. I have 5 years of Docker."}
    ).json()
    assert edited["edited"] is True
    assert any("Docker" in w for w in edited["warnings"])

    calls = len(provider.calls)
    kept = client.post(f"/jobs/{job_id}/cover-letter", json={"tone": "friendly"}).json()
    assert kept["body"] == edited["body"]  # edits are never overwritten without regenerate
    assert len(provider.calls) == calls

    pdf = client.get(f"/jobs/{job_id}/cover-letter/friendly/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get(f"/jobs/{job_id}/cover-letter/confident/pdf").status_code == 404
    assert set(client.get(f"/jobs/{job_id}").json()["cover_letters"]) == {"friendly"}


def test_cover_letter_validation(client: TestClient) -> None:
    job_id, _ = _job(client)
    assert client.post(f"/jobs/{job_id}/cover-letter", json={"tone": "sarcastic"}).status_code == 422
    assert client.put(f"/jobs/{job_id}/cover-letter/friendly", json={"body": "x" * 50}).status_code == 404


def test_interview_prep_only_links_real_projects(client: TestClient) -> None:
    job_id, provider = _job(client, QUESTIONS)
    res = client.post(f"/jobs/{job_id}/interview-prep")
    assert res.status_code == 200, res.text
    questions = res.json()["questions"]
    assert len(questions) == 8
    assert questions[0]["project"] == "Bot"  # matched case-insensitively to the real project
    assert questions[1]["project"] == ""  # "Ghost" isn't a real project
    assert client.get("/jobs").json()[0]["has_interview_prep"] is True

    provider.replies.append(QUESTIONS)
    regenerated = client.post(f"/jobs/{job_id}/interview-prep", json={"regenerate": True}).json()
    assert regenerated["generated_at"] != res.json()["generated_at"]
