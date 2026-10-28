"""Deterministic skill matching and the scoring formula."""

import pytest

from app.schemas.profile import ExperienceItem, ProfileData, ProjectItem
from app.services.matching import (
    NEUTRAL_SCORE,
    compute_score,
    find_evidence,
    match_skills,
    mentions,
    normalize_skill,
    profile_sources,
)

PROFILE = ProfileData(
    skills=["Python 3", "ReactJS", "PostgreSQL", "Go"],
    experience=[ExperienceItem(company="Acme", bullets=["Built REST APIs with FastAPI", "Wrote unit tests in pytest"])],
    projects=[
        ProjectItem(name="Chatbot", tech_stack=["LangChain", "Docker"], bullets=["Deployed on AWS Lambda"]),
    ],
    summary="Student who enjoys machine learning.",
)
SOURCES = profile_sources(PROFILE)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("ReactJS", "react"), ("  Node ", "node.js"), ("Postgres", "postgresql"), ("REST APIs", "rest api"), ("K8s", "kubernetes")],
)
def test_normalize_skill_aliases(raw: str, expected: str) -> None:
    assert normalize_skill(raw) == expected


def test_whole_term_search_avoids_false_positives() -> None:
    assert mentions("I write JavaScript daily", "javascript")
    assert not mentions("I write JavaScript daily", "java")
    assert not mentions("Used PostgreSQL", "sql")
    assert mentions("Built with Next.js.", "next.js")
    assert mentions("C++ and C#", "c++")


def test_evidence_priority_and_labels() -> None:
    assert find_evidence("Python", SOURCES) == "Listed in your skills"  # "Python 3" mentions python
    assert find_evidence("React", SOURCES) == "Listed in your skills"  # alias of ReactJS
    assert find_evidence("Docker", SOURCES) == "Tech stack of “Chatbot”"
    assert find_evidence("FastAPI", SOURCES) == "Used in your role at Acme"
    assert find_evidence("AWS", SOURCES) == "Used in project “Chatbot”"
    assert find_evidence("Machine Learning", SOURCES) == "Mentioned in your summary"


def test_rest_api_alias_matches_plural_in_text() -> None:
    assert find_evidence("RESTful APIs", SOURCES) == "Used in your role at Acme"


def test_short_skills_only_match_list_items() -> None:
    assert find_evidence("Go", SOURCES) == "Listed in your skills"
    other = profile_sources(ProfileData(summary="Ready to go build things"))
    assert find_evidence("Go", other) is None


def test_missing_skills_are_not_invented() -> None:
    assert find_evidence("Kubernetes", SOURCES) is None
    assert find_evidence("SQL", SOURCES) is None  # PostgreSQL is left for the verified semantic step


def test_match_skills_keeps_order() -> None:
    matched, missing = match_skills(["Docker", "Kubernetes", "Python", "Rust"], SOURCES)
    assert [m.skill for m in matched] == ["Docker", "Python"]
    assert missing == ["Kubernetes", "Rust"]
    assert all(m.direct for m in matched)


def test_perfect_entry_match_is_100() -> None:
    assert compute_score(4, 4, 2, 2, "entry")[0] == 100


def test_no_matches_entry_level() -> None:
    score, _ = compute_score(4, 0, 2, 0, "entry")
    assert score == 10  # only the seniority component remains


def test_missing_nice_to_haves_are_reweighted() -> None:
    # No nice-to-haves listed: required 0.7 + seniority 0.1, renormalised over 0.8.
    assert compute_score(2, 2, 0, 0, "entry")[0] == 100
    assert compute_score(2, 1, 0, 0, "entry")[0] == round(100 * (0.7 * 0.5 + 0.1) / 0.8)


def test_seniority_lowers_score() -> None:
    entry, _ = compute_score(4, 3, 2, 1, "entry")
    senior, breakdown = compute_score(4, 3, 2, 1, "senior")
    assert senior < entry
    assert breakdown.seniority_fit == 0.2


def test_no_skills_listed_gives_neutral_score() -> None:
    score, breakdown = compute_score(0, 0, 0, 0, "internship")
    assert score == NEUTRAL_SCORE
    assert breakdown.required_total == 0


def test_score_is_bounded() -> None:
    for args in [(1, 1, 1, 1, "internship"), (10, 0, 10, 0, "senior"), (3, 2, 5, 4, "mid")]:
        score, _ = compute_score(*args)
        assert 0 <= score <= 100
