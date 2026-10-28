"""Demo data is opt-in and removing it never touches a real profile."""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.services.seed import remove_demo_profile, seed_demo_profile


def test_no_demo_profile_by_default(client: TestClient) -> None:
    assert client.get("/profile").status_code == 404


def test_remove_demo_profile(client: TestClient) -> None:
    with SessionLocal() as db:
        assert seed_demo_profile(db) is True
        assert remove_demo_profile(db) is True
    assert client.get("/profile").status_code == 404


def test_real_profile_is_never_removed(client: TestClient) -> None:
    client.put("/profile", json={"full_name": "Salman", "skills": ["Python"]})
    with SessionLocal() as db:
        assert remove_demo_profile(db) is False
    assert client.get("/profile").json()["full_name"] == "Salman"


def test_edited_demo_profile_becomes_real(client: TestClient) -> None:
    with SessionLocal() as db:
        seed_demo_profile(db)
    client.put("/profile", json={"full_name": "Salman"})
    with SessionLocal() as db:
        assert remove_demo_profile(db) is False
    assert client.get("/profile").json()["is_demo"] is False
