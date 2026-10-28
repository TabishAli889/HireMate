"""ProfileData validation: cleaning, defaults and limits."""

import pytest
from pydantic import ValidationError

from app.schemas.profile import ExperienceItem, ProfileData


def test_defaults_are_empty_not_invented() -> None:
    profile = ProfileData()
    assert profile.full_name == ""
    assert profile.skills == []
    assert profile.experience == []


def test_skills_are_trimmed_and_deduplicated_case_insensitively() -> None:
    profile = ProfileData(skills=["  Python ", "python", "FastAPI", "", "Fast  API", "fastapi"])
    assert profile.skills == ["Python", "FastAPI", "Fast API"]


def test_blank_bullets_are_dropped() -> None:
    item = ExperienceItem(company="Acme", bullets=["Built X", "   ", "", "Built X"])
    assert item.bullets == ["Built X"]


def test_strings_are_stripped() -> None:
    assert ProfileData(full_name="  Salman  ").full_name == "Salman"


def test_overlong_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProfileData(full_name="x" * 301)


def test_parses_llm_style_json() -> None:
    raw = (
        '{"full_name":"Sara","skills":["SQL"],'
        '"experience":[{"company":"Acme","title":"Intern","bullets":["Did a thing"]}],'
        '"projects":[{"name":"Bot","tech_stack":["Python","python"]}]}'
    )
    profile = ProfileData.model_validate_json(raw)
    assert profile.experience[0].title == "Intern"
    assert profile.projects[0].tech_stack == ["Python"]
    assert profile.education == []


def test_wrong_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProfileData.model_validate_json('{"skills": "Python, SQL"}')
