"""Phase 6: the application tracker board."""

import json

from fastapi.testclient import TestClient

from tests.conftest import use_fake_llm

POSTING = "Nimbus Analytics is hiring a Backend Intern. Python, REST APIs and Docker required."
EXTRACTED = json.dumps(
    {"title": "Backend Intern", "company": "Nimbus Analytics", "required_skills": ["Python", "REST APIs", "Docker"]}
)


def _job(client: TestClient) -> int:
    use_fake_llm(EXTRACTED)
    return client.post("/jobs/analyze", json={"text": POSTING}).json()["id"]


def _add(client: TestClient, title: str, **extra: object) -> dict:
    res = client.post("/applications", json={"title": title, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def _column(client: TestClient, status: str) -> list[str]:
    return [a["title"] for a in client.get("/applications").json() if a["status"] == status]


def test_add_analyzed_job_uses_its_details(client: TestClient) -> None:
    job_id = _job(client)
    res = client.post("/applications", json={"job_id": job_id})
    assert res.status_code == 201, res.text
    card = res.json()
    assert (card["title"], card["company"], card["status"]) == ("Backend Intern", "Nimbus Analytics", "saved")
    assert card["events"][0]["message"] == "Added to Saved"

    # The job knows it's on the board, and can't be added twice.
    assert client.get(f"/jobs/{job_id}").json()["application"] == {"id": card["id"], "status": "saved"}
    assert client.get("/jobs").json()[0]["application_status"] == "saved"
    duplicate = client.post("/applications", json={"job_id": job_id})
    assert duplicate.status_code == 409
    assert "already on your board" in duplicate.json()["detail"]


def test_manual_card_needs_a_title_and_valid_link(client: TestClient) -> None:
    assert client.post("/applications", json={"company": "Acme"}).status_code == 422
    assert client.post("/applications", json={"title": "Intern", "link": "javascript:alert(1)"}).status_code == 422
    card = _add(client, "ML Intern", company="Acme", link="https://acme.example/jobs/1", status="applied", deadline="2026-11-12")
    assert card["status"] == "applied"
    assert card["job_id"] is None and card["match_score"] is None
    assert [e["message"] for e in card["events"]] == ["Added to Applied", "Deadline set to 12 Nov 2026"]


def test_move_reorders_columns_and_logs_status_changes(client: TestClient) -> None:
    a, b, c = (_add(client, name) for name in ("A", "B", "C"))
    assert _column(client, "saved") == ["A", "B", "C"]

    # Reorder inside a column: C to the top. No timeline entry for a reorder.
    moved = client.post(f"/applications/{c['id']}/move", json={"status": "saved", "position": 0}).json()
    assert _column(client, "saved") == ["C", "A", "B"]
    assert len(moved["events"]) == 1

    # Move to another column; the old column closes the gap.
    moved = client.post(f"/applications/{a['id']}/move", json={"status": "interview", "position": 5}).json()
    assert moved["events"][-1]["message"] == "Moved from Saved to Interview"
    assert _column(client, "saved") == ["C", "B"]
    assert _column(client, "interview") == ["A"]
    positions = {x["title"]: x["position"] for x in client.get("/applications").json()}
    assert positions == {"C": 0, "B": 1, "A": 0}

    client.post(f"/applications/{b['id']}/move", json={"status": "interview", "position": 0})
    assert _column(client, "interview") == ["B", "A"]
    assert client.post(f"/applications/{b['id']}/move", json={"status": "ghosted"}).status_code == 422


def test_update_notes_deadline_and_details(client: TestClient) -> None:
    card = _add(client, "Data Intern")
    url = f"/applications/{card['id']}"

    updated = client.patch(url, json={"notes": "Recruiter: Ali", "deadline": "2026-12-01", "company": "Beta"}).json()
    assert (updated["notes"], updated["deadline"], updated["company"]) == ("Recruiter: Ali", "2026-12-01", "Beta")
    assert [e["kind"] for e in updated["events"]] == ["created", "details", "notes", "deadline"]

    # Unchanged values add nothing; null clears the deadline.
    same = client.patch(url, json={"notes": "Recruiter: Ali"}).json()
    assert len(same["events"]) == 4
    cleared = client.patch(url, json={"deadline": None}).json()
    assert cleared["deadline"] is None
    assert cleared["events"][-1]["message"] == "Deadline removed"


def test_delete_closes_the_gap(client: TestClient) -> None:
    a, b = _add(client, "A"), _add(client, "B")
    assert client.delete(f"/applications/{a['id']}").status_code == 204
    assert client.get(f"/applications/{a['id']}").status_code == 404
    assert client.get(f"/applications/{b['id']}").json()["position"] == 0


def test_board_includes_job_documents_and_score(client: TestClient) -> None:
    job_id = _job(client)
    client.post("/applications", json={"job_id": job_id})
    card = client.get("/applications").json()[0]
    assert card["job_id"] == job_id
    assert card["has_tailoring"] is False and card["match_score"] is None
