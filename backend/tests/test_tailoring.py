"""Tailoring post-processing, project ranking, PDF export and the cover letter composer (no network)."""

import io
from datetime import datetime, timezone

import pdfplumber

from app.schemas.documents import BulletSuggestion, ProjectRankDraft, RankedProject, TailoredBulletDraft, TailoringDraft, TailoringResult
from app.schemas.job import JobRequirements
from app.schemas.profile import ExperienceItem, ProfileData, ProjectItem
from app.services.cover_letter import compose_letter
from app.services.pdf_export import render_letter_pdf, render_resume_pdf
from app.services.tailoring import apply_accepted, build_suggestions, rank_projects, source_bullets

PROFILE = ProfileData(
    full_name="Sara Ahmed",
    email="sara@example.com",
    skills=["Python", "FastAPI"],
    experience=[ExperienceItem(company="Acme", title="Intern", bullets=["Made APIs for the HR team", "Fixed bugs"])],
    projects=[
        ProjectItem(name="Bot", bullets=["Built a chatbot with LangChain"]),
        ProjectItem(name="Splitter", bullets=["Built an expense app"]),
    ],
)
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_source_bullet_ids_are_stable() -> None:
    assert [(s.id, s.context) for s in source_bullets(PROFILE)] == [
        ("exp0-b0", "Intern at Acme"),
        ("exp0-b1", "Intern at Acme"),
        ("proj0-b0", "Project: Bot"),
        ("proj1-b0", "Project: Splitter"),
    ]


def test_build_suggestions_applies_honesty_guard() -> None:
    draft = TailoringDraft(
        bullets=[
            TailoredBulletDraft(id="exp0-b0", rewritten="Built REST APIs with FastAPI for the HR team", reason="REST APIs"),
            TailoredBulletDraft(id="exp0-b1", rewritten="Fixed 25 production bugs", reason="quality"),  # invented number
            TailoredBulletDraft(id="proj0-b0", rewritten="Built a LangChain chatbot deployed with Docker"),  # missing skill
            TailoredBulletDraft(id="nope-b9", rewritten="Invented bullet"),  # unknown id: ignored
        ]
    )
    suggestions = {s.id: s for s in build_suggestions(source_bullets(PROFILE), draft, ["Docker"])}

    assert set(suggestions) == {"exp0-b0", "exp0-b1", "proj0-b0", "proj1-b0"}
    assert suggestions["exp0-b0"].tailored.startswith("Built REST APIs")
    assert suggestions["exp0-b0"].status == "pending"
    for rejected in ("exp0-b1", "proj0-b0"):
        assert suggestions[rejected].tailored == suggestions[rejected].original
        assert suggestions[rejected].guard_note.startswith("Kept your original")
        assert suggestions[rejected].status == "accepted"  # unchanged bullets need no decision
    assert suggestions["proj1-b0"].tailored == "Built an expense app"


def test_rank_projects_ignores_invented_names_and_keeps_all_real_ones() -> None:
    draft = TailoringDraft(project_ranking=[ProjectRankDraft(name="splitter", reason="SQL"), ProjectRankDraft(name="Fake App")])
    assert [(p.name, p.rank) for p in rank_projects(PROFILE, draft)] == [("Splitter", 1), ("Bot", 2)]


def _tailoring(status: str) -> TailoringResult:
    bullet = BulletSuggestion(
        id="exp0-b0", section="experience", context="Intern at Acme", original="Made APIs for the HR team",
        tailored="Built REST APIs for the HR team", status=status,  # type: ignore[arg-type]
    )
    return TailoringResult(
        bullets=[bullet], projects=[RankedProject(name="Splitter", rank=1), RankedProject(name="Bot", rank=2)], generated_at=NOW
    )


def test_apply_accepted_only_uses_accepted_rewrites() -> None:
    accepted = apply_accepted(PROFILE, _tailoring("accepted"))
    assert accepted.experience[0].bullets[0] == "Built REST APIs for the HR team"
    assert [p.name for p in accepted.projects] == ["Splitter", "Bot"]
    rejected = apply_accepted(PROFILE, _tailoring("rejected"))
    assert rejected.experience[0].bullets[0] == "Made APIs for the HR team"


def _pdf_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_resume_pdf_contains_tailored_content() -> None:
    data = render_resume_pdf(apply_accepted(PROFILE, _tailoring("accepted")))
    assert data.startswith(b"%PDF")
    text = _pdf_text(data)
    assert "Sara Ahmed" in text
    assert "Built REST APIs for the HR team" in text
    assert text.index("Splitter") < text.index("Bot")


def test_cover_letter_compose_and_pdf() -> None:
    body = compose_letter(["Para one about the role.", "Para two about Bot.", "Thanks & regards <3"], PROFILE, JobRequirements(company="Nimbus"))
    assert body.startswith("Dear Hiring Team at Nimbus,")
    assert body.endswith("Sincerely,\nSara Ahmed")
    text = _pdf_text(render_letter_pdf(PROFILE, body))
    assert "Para two about Bot." in text
    assert "Thanks & regards <3" in text  # special characters are escaped, not swallowed
