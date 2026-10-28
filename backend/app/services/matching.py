"""Deterministic skill matching and scoring — no LLM, fully unit-tested.

A job skill counts as matched only when the profile shows it: in the skills list, a project's
tech stack, or the text of a bullet/summary. The score is a weighted coverage formula, so the
same profile + job always gives the same number.
"""

import re
from dataclasses import dataclass

from app.schemas.job import MatchBreakdown, Seniority, SkillMatch
from app.schemas.profile import ProfileData

REQUIRED_WEIGHT = 0.7
NICE_WEIGHT = 0.2
SENIORITY_WEIGHT = 0.1
NEUTRAL_SCORE = 50  # when a posting lists no concrete skills at all

# HireMate targets students and fresh graduates, so senior roles are a weaker fit.
SENIORITY_FIT: dict[str, float] = {"internship": 1.0, "entry": 1.0, "unknown": 0.8, "mid": 0.5, "senior": 0.2}

# Skills shorter than this ("Go", "R", "C") only match exact list items, never free text.
MIN_TEXT_MATCH_LEN = 3

ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nextjs": "next.js",
    "nodejs": "node.js",
    "node": "node.js",
    "expressjs": "express.js",
    "express": "express.js",
    "vuejs": "vue.js",
    "vue": "vue.js",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "golang": "go",
    "py": "python",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "llms": "llm",
    "large language models": "llm",
    "large language model": "llm",
    "genai": "generative ai",
    "gen ai": "generative ai",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "amazon web services": "aws",
    "gcp": "google cloud",
    "google cloud platform": "google cloud",
    "cicd": "ci/cd",
    "ci-cd": "ci/cd",
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "hugging face": "huggingface",
    "c sharp": "c#",
    "dotnet": ".net",
    ".net core": ".net",
}


def _clean(text: str) -> str:
    return " ".join(text.casefold().split()).strip(" ,;:")


def normalize_skill(skill: str) -> str:
    """Lowercase, trim and map known aliases to one canonical name ("ReactJS" -> "react")."""
    cleaned = _clean(skill).rstrip(".")
    return ALIASES.get(cleaned, cleaned)


def skill_variants(skill: str) -> set[str]:
    """All spellings worth searching for: the canonical name, the raw form and every alias."""
    canonical = normalize_skill(skill)
    variants = {canonical, _clean(skill).rstrip(".")}
    variants.update(alias for alias, target in ALIASES.items() if target == canonical)
    return {v for v in variants if v}


@dataclass(frozen=True)
class EvidenceSource:
    """One piece of profile text plus a human label saying where it came from."""

    label: str
    text: str


def profile_sources(profile: ProfileData) -> list[EvidenceSource]:
    """Profile text in priority order: explicit lists first, then experience, projects, summary, education."""
    sources = [EvidenceSource("Listed in your skills", skill) for skill in profile.skills]
    for project in profile.projects:
        name = project.name or "a project"
        sources += [EvidenceSource(f"Tech stack of “{name}”", tech) for tech in project.tech_stack]
    for job in profile.experience:
        where = f"your role at {job.company}" if job.company else "your experience"
        sources += [EvidenceSource(f"Used in {where}", bullet) for bullet in job.bullets]
    for project in profile.projects:
        name = project.name or "a project"
        texts = [project.description, *project.bullets]
        sources += [EvidenceSource(f"Used in project “{name}”", text) for text in texts if text]
    if profile.summary:
        sources.append(EvidenceSource("Mentioned in your summary", profile.summary))
    for edu in profile.education:
        text = " ".join(part for part in (edu.degree, edu.field_of_study, edu.details) if part)
        if text:
            sources.append(EvidenceSource("Mentioned in your education", text))
    return sources


def mentions(text: str, variant: str) -> bool:
    """Whole-term search: 'java' is not found inside 'javascript', 'sql' not inside 'postgresql'."""
    pattern = rf"(?<![a-z0-9+#]){re.escape(variant)}(?![a-z0-9+#])"
    return re.search(pattern, text.casefold()) is not None


def find_evidence(skill: str, sources: list[EvidenceSource]) -> str | None:
    """Label of the first source that shows `skill`, or None."""
    canonical = normalize_skill(skill)
    searchable = [v for v in skill_variants(skill) if len(v) >= MIN_TEXT_MATCH_LEN]
    for source in sources:
        if normalize_skill(source.text) == canonical:
            return source.label
        if any(mentions(source.text, variant) for variant in searchable):
            return source.label
    return None


def match_skills(job_skills: list[str], sources: list[EvidenceSource]) -> tuple[list[SkillMatch], list[str]]:
    """Split job skills into (matched with evidence, missing), preserving the posting's order."""
    matched: list[SkillMatch] = []
    missing: list[str] = []
    for skill in job_skills:
        evidence = find_evidence(skill, sources)
        if evidence:
            matched.append(SkillMatch(skill=skill, evidence=evidence, direct=True))
        else:
            missing.append(skill)
    return matched, missing


def compute_score(
    required_total: int,
    required_matched: int,
    nice_total: int,
    nice_matched: int,
    seniority: Seniority,
) -> tuple[int, MatchBreakdown]:
    """Weighted coverage: 70% required skills, 20% nice-to-haves, 10% seniority fit.

    Missing components (e.g. no nice-to-haves listed) are dropped and the rest re-weighted.
    """
    fit = SENIORITY_FIT.get(seniority, SENIORITY_FIT["unknown"])
    parts: list[tuple[float, float]] = []
    if required_total:
        parts.append((REQUIRED_WEIGHT, required_matched / required_total))
    if nice_total:
        parts.append((NICE_WEIGHT, nice_matched / nice_total))

    if not parts:
        score = NEUTRAL_SCORE
    else:
        parts.append((SENIORITY_WEIGHT, fit))
        total_weight = sum(weight for weight, _ in parts)
        score = round(100 * sum(weight * coverage for weight, coverage in parts) / total_weight)

    breakdown = MatchBreakdown(
        required_matched=required_matched,
        required_total=required_total,
        nice_matched=nice_matched,
        nice_total=nice_total,
        seniority=seniority,
        seniority_fit=fit,
    )
    return max(0, min(100, score)), breakdown
