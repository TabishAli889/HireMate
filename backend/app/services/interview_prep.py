"""`generate_interview_questions` tool: 8 likely questions with hints grounded in the user's real projects."""

import json
from datetime import datetime, timezone

from app.schemas.documents import InterviewPrep, InterviewPrepDraft, InterviewQuestion
from app.schemas.job import JobRequirements, MatchResult
from app.schemas.profile import ProfileData
from app.services.llm import LLMProvider, generate_structured
from app.services.text_clean import normalize_text

QUESTION_COUNT = 8

INTERVIEW_INSTRUCTIONS = """
You prepare a student for an interview for one specific job, for HireMate.

Write 8 likely interview questions: a mix of technical (the job's required skills), project (deep dives into
the candidate's own projects), behavioral, and role/company questions.

For each question, `hint` is 2-3 sentences on how THIS candidate should answer:
- Point to a specific real project or role from their profile when one fits, and set `project` to that project's
  exact name (or leave `project` empty).
- For skills the candidate is missing, suggest an honest answer: what they know that's related and how they would learn it.
  Never suggest claiming experience they don't have.
- Never invent projects, metrics or employers.
""".strip()


def generate_interview_questions(
    provider: LLMProvider,
    profile: ProfileData,
    job: JobRequirements,
    match: MatchResult | None,
    *,
    fingerprint: str,
    max_retries: int = 2,
) -> InterviewPrep:
    payload = {
        "job": {
            "title": job.title,
            "company": job.company,
            "seniority": job.seniority,
            "required_skills": job.required_skills,
            "responsibilities": job.responsibilities,
        },
        "candidate_skills": profile.skills,
        "candidate_projects": [{"name": p.name, "description": p.description, "tech_stack": p.tech_stack} for p in profile.projects],
        "candidate_experience": [{"title": e.title, "company": e.company} for e in profile.experience],
        "missing_skills": (match.missing_required + match.missing_nice) if match else [],
    }
    draft = generate_structured(
        provider,
        InterviewPrepDraft,
        instructions=INTERVIEW_INSTRUCTIONS,
        user_content=json.dumps(payload, ensure_ascii=False),
        max_retries=max_retries,
    )
    project_names = {p.name.casefold(): p.name for p in profile.projects if p.name}
    questions = [
        InterviewQuestion(
            question=normalize_text(q.question),
            category=q.category,
            hint=normalize_text(q.hint),
            project=project_names.get(q.project.casefold().strip(), ""),  # only real projects
        )
        for q in draft.questions[:QUESTION_COUNT]
    ]
    return InterviewPrep(questions=questions, generated_at=datetime.now(timezone.utc), profile_fingerprint=fingerprint)
