"""Code-enforced honesty checks for AI-written text. The prompts ask for honesty; these functions verify it.

- A rewritten bullet may not add numbers that weren't in the original (metrics must be "[add real number]").
- A rewritten bullet may not mention a skill the profile is missing (that would claim experience you don't have).
- A cover letter is scanned for the same problems and the user is warned.
"""

import re

from app.schemas.documents import METRIC_PLACEHOLDER
from app.services.matching import mentions, skill_variants

_NUMBER = re.compile(r"(?<![a-z])\d+(?:[.,]\d+)*\s*(?:%|\+|k\b|x\b)?", re.IGNORECASE)


def numbers_in(text: str) -> set[str]:
    """Numbers as written, normalised (e.g. "30 %" -> "30%")."""
    cleaned = text.replace(METRIC_PLACEHOLDER, " ")
    return {re.sub(r"\s+", "", match.group(0)).lower() for match in _NUMBER.finditer(cleaned)}


def new_numbers(original: str, rewritten: str) -> list[str]:
    """Numbers in `rewritten` that never appear in `original`."""
    known = numbers_in(original)
    return sorted(n for n in numbers_in(rewritten) if n not in known and n.rstrip("%+kx") not in known)


def mentioned_skills(text: str, skills: list[str]) -> list[str]:
    """Which of `skills` the text mentions (whole-term, alias-aware)."""
    return [skill for skill in skills if any(len(v) >= 2 and mentions(text, v) for v in skill_variants(skill))]


def bullet_violation(original: str, rewritten: str, missing_skills: list[str]) -> str | None:
    """Why a rewrite must be rejected, or None if it only rephrases what's already there."""
    added = new_numbers(original, rewritten)
    if added:
        return f"the rewrite added a number ({', '.join(added)}) that isn't in your resume"
    claimed = [s for s in mentioned_skills(rewritten, missing_skills) if s not in mentioned_skills(original, missing_skills)]
    if claimed:
        return f"the rewrite mentioned {', '.join(claimed)}, which your profile doesn't show"
    return None


def letter_warnings(body: str, profile_text: str, missing_skills: list[str]) -> list[str]:
    """Things in a cover letter the user should double-check before sending."""
    warnings: list[str] = []
    for skill in mentioned_skills(body, missing_skills):
        warnings.append(f"Mentions {skill}, which isn't in your profile. Make sure the letter doesn't claim experience with it.")
    unknown = sorted(n for n in numbers_in(body) if n not in numbers_in(profile_text))
    if unknown:
        warnings.append(f"Contains numbers not found in your profile ({', '.join(unknown)}). Check they are accurate.")
    if METRIC_PLACEHOLDER in body:
        warnings.append(f"Replace every “{METRIC_PLACEHOLDER}” with a real figure, or remove it.")
    return warnings
