"""`tailor_bullets` tool: rewrite the user's EXISTING bullets for one job and rank their projects.

Every rewrite is checked in code (honesty.bullet_violation); a rewrite that adds a number or a missing
skill is discarded and the original bullet is kept, with a note explaining why.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.documents import METRIC_PLACEHOLDER, BulletSuggestion, RankedProject, TailoringDraft, TailoringResult
from app.schemas.job import JobRequirements, MatchResult
from app.schemas.profile import ProfileData
from app.services.honesty import bullet_violation
from app.services.llm import LLMProvider, generate_structured
from app.services.text_clean import normalize_text

MAX_BULLETS = 40

TAILOR_INSTRUCTIONS = f"""
You tailor a student's resume bullets to one job posting for HireMate.

STRICT HONESTY RULES:
- Rewrite ONLY the bullets given. Keep each bullet's facts: same work, same tools, same scope, same results.
- NEVER add skills, tools, employers, responsibilities, results or numbers that the original bullet doesn't state.
- Never mention the job's missing skills (listed below) unless the original bullet already mentions them.
- If a stronger bullet would need a metric the original doesn't have, write "{METRIC_PLACEHOLDER}" instead of a number.
- If a bullet is already good or isn't relevant to this job, return it unchanged.

HOW TO TAILOR:
- Lead with a strong action verb; put the parts most relevant to this job first.
- Use the job's wording for skills the candidate genuinely has (e.g. "REST APIs" instead of "endpoints").
- Keep each bullet to one sentence, at most about 30 words.
- reason: a short phrase naming the job requirement the bullet now highlights.

project_ranking: every project name, most relevant to this job first, each with a short reason.
Return one item in `bullets` for every bullet id you were given.
""".strip()


@dataclass(frozen=True)
class SourceBullet:
    id: str
    section: str
    context: str
    text: str


def source_bullets(profile: ProfileData) -> list[SourceBullet]:
    """All experience and project bullets with stable ids like exp0-b1 / proj2-b0."""
    items: list[SourceBullet] = []
    for i, job in enumerate(profile.experience):
        context = " at ".join(part for part in (job.title, job.company) if part) or f"Experience {i + 1}"
        items += [SourceBullet(f"exp{i}-b{j}", "experience", context, text) for j, text in enumerate(job.bullets)]
    for i, project in enumerate(profile.projects):
        context = f"Project: {project.name or f'Project {i + 1}'}"
        items += [SourceBullet(f"proj{i}-b{j}", "project", context, text) for j, text in enumerate(project.bullets)]
    return items[:MAX_BULLETS]


def build_suggestions(
    sources: list[SourceBullet], draft: TailoringDraft, missing_skills: list[str]
) -> list[BulletSuggestion]:
    """Pair every original bullet with its rewrite, rejecting rewrites that fail the honesty check."""
    rewrites = {item.id: item for item in draft.bullets}
    suggestions: list[BulletSuggestion] = []
    for source in sources:
        rewrite = rewrites.get(source.id)
        tailored, reason, note = source.text, "", ""
        rewritten = normalize_text(rewrite.rewritten).strip() if rewrite is not None else ""
        if rewritten:
            problem = bullet_violation(source.text, rewritten, missing_skills)
            if problem:
                note = f"Kept your original: {problem}."
            else:
                tailored, reason = rewritten, normalize_text(rewrite.reason)
        changed = tailored.strip() != source.text.strip()
        suggestions.append(
            BulletSuggestion(
                id=source.id,
                section=source.section,  # type: ignore[arg-type]
                context=source.context,
                original=source.text,
                tailored=tailored,
                reason=reason if changed else "",
                status="pending" if changed else "accepted",
                guard_note=note,
            )
        )
    return suggestions


def rank_projects(profile: ProfileData, draft: TailoringDraft) -> list[RankedProject]:
    """The LLM's order for projects that exist, then any it forgot, in profile order."""
    names = [p.name for p in profile.projects if p.name]
    by_key = {name.casefold(): name for name in names}
    ranked: list[RankedProject] = []
    seen: set[str] = set()
    for item in draft.project_ranking:
        key = item.name.casefold().strip()
        if key in by_key and key not in seen:
            seen.add(key)
            ranked.append(RankedProject(name=by_key[key], rank=len(ranked) + 1, reason=item.reason))
    for name in names:
        if name.casefold() not in seen:
            ranked.append(RankedProject(name=name, rank=len(ranked) + 1))
    return ranked


def tailor_bullets(
    provider: LLMProvider,
    profile: ProfileData,
    job: JobRequirements,
    match: MatchResult,
    *,
    fingerprint: str,
    max_retries: int = 2,
) -> TailoringResult:
    sources = source_bullets(profile)
    missing = match.missing_required + match.missing_nice
    if not sources and not profile.projects:
        return TailoringResult(bullets=[], projects=[], generated_at=datetime.now(timezone.utc), profile_fingerprint=fingerprint)

    payload = {
        "job": {"title": job.title, "company": job.company, "summary": job.summary, "responsibilities": job.responsibilities},
        "skills_the_candidate_has_for_this_job": [m.skill for m in match.matched_skills],
        "missing_skills_never_mention": missing,
        "bullets": [{"id": s.id, "context": s.context, "text": s.text} for s in sources],
        "projects": [{"name": p.name, "description": p.description, "tech_stack": p.tech_stack} for p in profile.projects],
    }
    draft = generate_structured(
        provider,
        TailoringDraft,
        instructions=TAILOR_INSTRUCTIONS,
        user_content=json.dumps(payload, ensure_ascii=False),
        max_retries=max_retries,
    )
    return TailoringResult(
        bullets=build_suggestions(sources, draft, missing),
        projects=rank_projects(profile, draft),
        generated_at=datetime.now(timezone.utc),
        profile_fingerprint=fingerprint,
    )


def apply_accepted(profile: ProfileData, tailoring: TailoringResult) -> ProfileData:
    """Profile copy with accepted rewrites swapped in and projects in ranked order (for PDF export)."""
    accepted = {b.id: b.tailored for b in tailoring.bullets if b.status == "accepted"}
    experience = [
        job.model_copy(update={"bullets": [accepted.get(f"exp{i}-b{j}", text) for j, text in enumerate(job.bullets)]})
        for i, job in enumerate(profile.experience)
    ]
    projects = [
        project.model_copy(update={"bullets": [accepted.get(f"proj{i}-b{j}", text) for j, text in enumerate(project.bullets)]})
        for i, project in enumerate(profile.projects)
    ]
    order = {p.name.casefold(): p.rank for p in tailoring.projects}
    projects.sort(key=lambda p: order.get(p.name.casefold(), len(order) + 1))
    return profile.model_copy(update={"experience": experience, "projects": projects})
