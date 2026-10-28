"""`write_cover_letter` tool: a cover letter in one of three tones, built only from the real profile."""

import json
from datetime import datetime, timezone

from app.schemas.documents import METRIC_PLACEHOLDER, CoverLetter, CoverLetterDraft, Tone
from app.schemas.job import JobRequirements, MatchResult
from app.schemas.profile import ProfileData
from app.services.honesty import letter_warnings
from app.services.llm import LLMProvider, generate_structured
from app.services.matching import profile_sources
from app.services.text_clean import normalize_text

TONE_GUIDE: dict[Tone, str] = {
    "professional": "Formal, polished and concise. Measured language, no slang.",
    "friendly": "Warm and conversational, but still polished. Shows genuine enthusiasm for the team and the work.",
    "confident": "Direct and assertive about real strengths. Strong verbs, no hedging, never arrogant or exaggerated.",
}

LETTER_INSTRUCTIONS = f"""
You write a cover letter body for a student or fresh graduate, for HireMate.

STRICT HONESTY RULES:
- Mention ONLY projects, experience, education and skills that appear in the candidate profile given to you.
- NEVER claim the missing skills listed. You may briefly say the candidate is keen to learn one or two of them.
- Never invent employers, titles, dates, metrics or achievements. If a number would help, write "{METRIC_PLACEHOLDER}".

FORMAT:
- Return 3 to 5 paragraphs, each 2-4 sentences. No greeting line and no sign-off (they are added for you).
- Paragraph 1: the role, the company, and why the candidate is interested.
- Middle paragraphs: 1-2 of the candidate's most relevant real projects or roles, tied to the job's needs.
- Last paragraph: a short, polite close inviting a conversation.
""".strip()


def profile_text(profile: ProfileData) -> str:
    return "\n".join(source.text for source in profile_sources(profile))


def compose_letter(paragraphs: list[str], profile: ProfileData, job: JobRequirements) -> str:
    greeting = f"Dear Hiring Team at {job.company}," if job.company else "Dear Hiring Manager,"
    signature = profile.full_name or "[Your name]"
    body = "\n\n".join(p.strip() for p in paragraphs if p.strip())
    return normalize_text(f"{greeting}\n\n{body}\n\nSincerely,\n{signature}")


def write_cover_letter(
    provider: LLMProvider,
    profile: ProfileData,
    job: JobRequirements,
    match: MatchResult,
    *,
    tone: Tone,
    fingerprint: str,
    max_retries: int = 2,
) -> CoverLetter:
    missing = match.missing_required + match.missing_nice
    payload = {
        "tone": f"{tone}: {TONE_GUIDE[tone]}",
        "job": {"title": job.title, "company": job.company, "summary": job.summary, "responsibilities": job.responsibilities},
        "candidate": {
            "name": profile.full_name,
            "headline": profile.headline,
            "summary": profile.summary,
            "skills_relevant_to_job": [m.skill for m in match.matched_skills],
            "experience": [{"title": e.title, "company": e.company, "bullets": e.bullets} for e in profile.experience],
            "projects": [{"name": p.name, "description": p.description, "bullets": p.bullets} for p in profile.projects],
            "education": [{"degree": e.degree, "institution": e.institution} for e in profile.education],
        },
        "missing_skills_never_claim": missing,
    }
    draft = generate_structured(
        provider,
        CoverLetterDraft,
        instructions=LETTER_INSTRUCTIONS,
        user_content=json.dumps(payload, ensure_ascii=False),
        max_retries=max_retries,
    )
    body = compose_letter(draft.paragraphs, profile, job)
    now = datetime.now(timezone.utc)
    return CoverLetter(
        tone=tone,
        body=body,
        warnings=letter_warnings(body, profile_text(profile), missing),
        edited=False,
        generated_at=now,
        updated_at=now,
        profile_fingerprint=fingerprint,
    )
