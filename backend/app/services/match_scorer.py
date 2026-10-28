"""`score_match` and `plan_skill_gaps` tools.

score_match:
1. Deterministic matching finds skills the profile shows directly (matching.py).
2. The LLM may propose *related* evidence for the rest, but each proposal must quote the profile
   verbatim; quotes are verified in code, so the LLM can't invent a match.
3. The score is computed in code. The LLM only writes the plain-language explanation.

plan_skill_gaps: an ordered learning plan for the missing skills (separate step, separate LLM call).
"""

import json
import logging
from datetime import datetime, timezone

from app.schemas.job import (
    GapItem,
    GapPlan,
    JobRequirements,
    MatchExplanation,
    MatchResult,
    SemanticCandidate,
    SemanticMatches,
    SkillMatch,
)
from app.schemas.profile import ProfileData
from app.services.llm import LLMProvider, generate_structured
from app.services.llm.errors import LLMOutputError
from app.services.matching import EvidenceSource, compute_score, match_skills, normalize_skill, profile_sources

logger = logging.getLogger("hiremate.match")

MAX_GAP_ITEMS = 6

HONESTY = """
HONESTY RULES:
- The score and the skill lists are already computed. Do not change or dispute them.
- Only describe skills in matched_skills as strengths. Never claim or imply the candidate has a missing skill.
- Do not invent experience, projects, employers or metrics.
""".strip()

SEMANTIC_INSTRUCTIONS = """
You check whether a candidate's profile DEMONSTRATES job skills that a keyword search did not find.

RULES:
- Only include a skill when the profile clearly shows it, e.g. "PostgreSQL" demonstrates "SQL",
  "built REST endpoints with FastAPI" demonstrates "REST APIs", "PyTorch" demonstrates "Deep Learning".
- evidence_quote MUST be copied EXACTLY, character for character, from the profile text (3-120 characters).
- Never infer a skill from a job title or from something the candidate "could probably do".
- If a skill is not clearly demonstrated, leave it out. An empty list is a fine answer.
- Use the job skill name exactly as given in the list.
""".strip()

EXPLANATION_INSTRUCTIONS = f"""
You are HireMate's career coach for students and fresh graduates.

{HONESTY}

explanation: 2-4 short sentences in plain language, addressed to the candidate as "you".
Say how strong the match is, name the main strengths, and the most important gaps.
""".strip()

GAP_PLAN_INSTRUCTIONS = f"""
You are HireMate's career coach for students and fresh graduates.

{HONESTY}

gap_plan: one item per missing skill worth learning, most important first (required before nice-to-have;
prefer skills that build on what they already know). At most 6 items. For each item:
- skill: the missing skill name exactly as given.
- why: one sentence on why it matters for THIS job.
- first_steps: 2-3 concrete steps, e.g. an official tutorial, or a small addition to one of their existing projects.
- estimated_time: realistic time to basic working knowledge, e.g. "3-5 days" or "1-2 weeks".
""".strip()


def _profile_digest(sources: list[EvidenceSource]) -> str:
    return "\n".join(f"- [{source.label}] {source.text}" for source in sources)


def _squash(text: str) -> str:
    return " ".join(text.casefold().split()).strip(" .\"'“”‘’")


def verify_semantic_matches(
    candidates: list[SemanticCandidate], unmatched: list[str], sources: list[EvidenceSource]
) -> list[SkillMatch]:
    """Keep only proposals for skills we asked about whose quote really appears in the profile."""
    corpus = _squash(" \n ".join(source.text for source in sources))
    wanted = {normalize_skill(skill): skill for skill in unmatched}
    accepted: list[SkillMatch] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = normalize_skill(candidate.skill)
        quote = _squash(candidate.evidence_quote)
        if key not in wanted or key in seen or len(quote) < 3 or quote not in corpus:
            continue
        seen.add(key)
        accepted.append(
            SkillMatch(skill=wanted[key], evidence=f"Related: “{candidate.evidence_quote.strip()[:200]}”", direct=False)
        )
    return accepted


def find_semantic_matches(
    provider: LLMProvider, unmatched: list[str], sources: list[EvidenceSource], *, max_retries: int
) -> list[SkillMatch]:
    """Ask for related evidence; if the LLM output stays invalid, continue without it."""
    if not unmatched or not sources:
        return []
    content = "Job skills to check:\n" + "\n".join(f"- {s}" for s in unmatched)
    content += f"\n\nCandidate profile:\n{_profile_digest(sources)}"
    try:
        result = generate_structured(
            provider, SemanticMatches, instructions=SEMANTIC_INSTRUCTIONS, user_content=content, max_retries=max_retries
        )
    except LLMOutputError:
        logger.warning("Semantic matching output invalid; continuing with keyword matches only")
        return []
    return verify_semantic_matches(result.matches, unmatched, sources)


def _fallback_explanation(score: int, req_matched: int, req_total: int, missing: list[str]) -> str:
    text = f"Your match score is {score}/100. You show {req_matched} of {req_total} required skills."
    if missing:
        text += f" The most important gaps are: {', '.join(missing[:4])}."
    return text


def write_explanation(
    provider: LLMProvider,
    *,
    job: JobRequirements,
    score: int,
    matched: list[SkillMatch],
    missing_required: list[str],
    missing_nice: list[str],
    max_retries: int,
) -> str:
    """Plain-language explanation; on invalid output, fall back to a computed summary."""
    payload = {
        "job": {"title": job.title, "company": job.company, "seniority": job.seniority, "summary": job.summary},
        "score": score,
        "matched_skills": [m.skill for m in matched],
        "missing_required": missing_required,
        "missing_nice_to_have": missing_nice,
    }
    try:
        result = generate_structured(
            provider,
            MatchExplanation,
            instructions=EXPLANATION_INSTRUCTIONS,
            user_content=json.dumps(payload, ensure_ascii=False),
            max_retries=max_retries,
        )
        return result.explanation
    except LLMOutputError:
        logger.warning("Explanation output invalid; using computed fallback")
        required_total = len(job.required_skills)
        return _fallback_explanation(score, required_total - len(missing_required), required_total, missing_required)


def _clean_gap_plan(items: list[GapItem], missing: list[str]) -> list[GapItem]:
    """Drop items for skills that aren't actually missing, dedupe, renumber 1..n."""
    allowed = {normalize_skill(skill): skill for skill in missing}
    seen: set[str] = set()
    cleaned: list[GapItem] = []
    for item in items:
        key = normalize_skill(item.skill)
        if key in allowed and key not in seen:
            seen.add(key)
            cleaned.append(item.model_copy(update={"priority": len(cleaned) + 1, "skill": allowed[key]}))
    return cleaned[:MAX_GAP_ITEMS]


def score_match(
    provider: LLMProvider,
    profile: ProfileData,
    job: JobRequirements,
    *,
    profile_updated_at: datetime,
    max_retries: int = 2,
) -> MatchResult:
    """Deterministic + verified semantic matches, computed score, LLM explanation. `gap_plan` is left empty."""
    sources = profile_sources(profile)
    req_matched, req_missing = match_skills(job.required_skills, sources)
    nice_matched, nice_missing = match_skills(job.nice_to_have_skills, sources)

    related = find_semantic_matches(provider, req_missing + nice_missing, sources, max_retries=max_retries)
    related_keys = {normalize_skill(m.skill): m for m in related}
    req_matched += [related_keys[normalize_skill(s)] for s in req_missing if normalize_skill(s) in related_keys]
    nice_matched += [related_keys[normalize_skill(s)] for s in nice_missing if normalize_skill(s) in related_keys]
    req_missing = [s for s in req_missing if normalize_skill(s) not in related_keys]
    nice_missing = [s for s in nice_missing if normalize_skill(s) not in related_keys]

    score, breakdown = compute_score(
        len(job.required_skills), len(req_matched), len(job.nice_to_have_skills), len(nice_matched), job.seniority
    )
    matched = req_matched + nice_matched
    explanation = write_explanation(
        provider,
        job=job,
        score=score,
        matched=matched,
        missing_required=req_missing,
        missing_nice=nice_missing,
        max_retries=max_retries,
    )

    return MatchResult(
        score=score,
        matched_skills=matched,
        missing_required=req_missing,
        missing_nice=nice_missing,
        breakdown=breakdown,
        explanation=explanation,
        gap_plan=[],
        profile_updated_at=profile_updated_at,
        scored_at=datetime.now(timezone.utc),
    )


def plan_skill_gaps(
    provider: LLMProvider,
    profile: ProfileData,
    job: JobRequirements,
    match: MatchResult,
    *,
    max_retries: int = 2,
) -> list[GapItem]:
    """Ordered learning plan for the match's missing skills ([] when nothing is missing or output stays invalid)."""
    missing = match.missing_required + match.missing_nice
    if not missing:
        return []
    payload = {
        "job": {"title": job.title, "seniority": job.seniority, "summary": job.summary},
        "missing_required": match.missing_required,
        "missing_nice_to_have": match.missing_nice,
        "candidate_skills": profile.skills,
        "candidate_projects": [p.name for p in profile.projects if p.name],
    }
    try:
        result = generate_structured(
            provider,
            GapPlan,
            instructions=GAP_PLAN_INSTRUCTIONS,
            user_content=json.dumps(payload, ensure_ascii=False),
            max_retries=max_retries,
        )
    except LLMOutputError:
        logger.warning("Gap plan output invalid; returning no plan")
        return []
    return _clean_gap_plan(result.gap_plan, missing)
