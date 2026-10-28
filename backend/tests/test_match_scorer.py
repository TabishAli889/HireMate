"""score_match: verified semantic matches, computed score, narrative and fallbacks."""

import json
from datetime import datetime, timezone

from app.schemas.job import JobRequirements, SemanticCandidate
from app.schemas.profile import ProfileData, ProjectItem
from app.services.match_scorer import plan_skill_gaps, score_match, verify_semantic_matches
from app.services.matching import compute_score, profile_sources
from tests.conftest import FakeProvider

PROFILE = ProfileData(
    skills=["Python", "PostgreSQL"],
    projects=[ProjectItem(name="Bot", bullets=["Built REST APIs with FastAPI"])],
)
JOB = JobRequirements(
    title="Backend Intern",
    seniority="internship",
    required_skills=["Python", "SQL", "REST APIs", "Docker"],
    nice_to_have_skills=["AWS"],
)
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)
SEMANTIC = json.dumps(
    {
        "matches": [
            {"skill": "SQL", "evidence_quote": "PostgreSQL"},
            {"skill": "Docker", "evidence_quote": "Deployed with Kubernetes"},  # fabricated quote
        ]
    }
)
EXPLANATION = json.dumps({"explanation": "You match most of the required skills for this internship."})
PLAN = json.dumps(
    {
        "gap_plan": [
            {"skill": "Kotlin", "why": "Not asked for", "first_steps": ["x"]},  # not missing -> dropped
            {"skill": "Docker", "priority": 7, "why": "Used to ship the API.", "first_steps": ["Containerise Bot"]},
            {"skill": "AWS", "why": "Nice to have.", "first_steps": ["Try free tier"], "estimated_time": "1 week"},
        ],
    }
)


def test_verify_rejects_fabricated_quotes_and_unasked_skills() -> None:
    sources = profile_sources(PROFILE)
    candidates = [
        SemanticCandidate(skill="SQL", evidence_quote="  postgresql "),
        SemanticCandidate(skill="Docker", evidence_quote="Deployed with Kubernetes"),
        SemanticCandidate(skill="Rust", evidence_quote="Python"),  # not in the unmatched list
        SemanticCandidate(skill="SQL", evidence_quote="PostgreSQL"),  # duplicate
    ]
    accepted = verify_semantic_matches(candidates, ["SQL", "Docker"], sources)
    assert [m.skill for m in accepted] == ["SQL"]
    assert accepted[0].direct is False
    assert "postgresql" in accepted[0].evidence


def test_score_then_plan() -> None:
    provider = FakeProvider([SEMANTIC, EXPLANATION, PLAN])
    result = score_match(provider, PROFILE, JOB, profile_updated_at=NOW)

    assert [m.skill for m in result.matched_skills] == ["Python", "REST APIs", "SQL"]
    assert result.missing_required == ["Docker"]
    assert result.missing_nice == ["AWS"]
    assert result.score == compute_score(4, 3, 1, 0, "internship")[0]
    assert result.gap_plan == []  # planning is a separate step
    assert len(provider.calls) == 2

    plan = plan_skill_gaps(provider, PROFILE, JOB, result)
    assert [(g.skill, g.priority) for g in plan] == [("Docker", 1), ("AWS", 2)]


def test_semantic_step_skipped_when_everything_matches() -> None:
    job = JobRequirements(title="Dev", required_skills=["Python"], seniority="entry")
    provider = FakeProvider([json.dumps({"explanation": "Great fit, you have the core skill."})])
    result = score_match(provider, PROFILE, job, profile_updated_at=NOW)
    assert result.score == 100
    assert len(provider.calls) == 1
    assert plan_skill_gaps(provider, PROFILE, job, result) == []  # nothing missing: no LLM call
    assert len(provider.calls) == 1


def test_invalid_llm_output_falls_back_gracefully() -> None:
    provider = FakeProvider(["bad"] * 9)  # semantic, explanation and plan: 3 bad tries each
    result = score_match(provider, PROFILE, JOB, profile_updated_at=NOW)
    assert result.missing_required == ["SQL", "Docker"]  # no unverified semantic matches
    assert f"{result.score}/100" in result.explanation
    assert plan_skill_gaps(provider, PROFILE, JOB, result) == []
