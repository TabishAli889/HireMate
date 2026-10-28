"""Store and reuse generated documents (tailoring, cover letters, interview prep) per job.

Same rule as scoring: a document is only regenerated when the profile content changed, or when the
user explicitly asks to regenerate. Shared by the HTTP endpoints and the agent tools.
"""

from datetime import datetime, timezone
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.models.document import JobDocument
from app.models.job import Job
from app.schemas.documents import (
    BulletStatus,
    CoverLetter,
    InterviewPrep,
    TailoringResult,
    Tone,
    TONES,
)
from app.schemas.job import JobRequirements, MatchResult
from app.schemas.profile import ProfileData
from app.services.cover_letter import profile_text, write_cover_letter
from app.services.honesty import letter_warnings
from app.services.interview_prep import generate_interview_questions
from app.services.job_service import get_match, profile_fingerprint, require_profile, score_or_reuse
from app.services.llm import LLMProvider
from app.services.tailoring import tailor_bullets

T = TypeVar("T", bound=BaseModel)

TAILORING = "tailoring"
INTERVIEW = "interview_prep"


def cover_letter_kind(tone: Tone) -> str:
    return f"cover_letter:{tone}"


def _find(job: Job, kind: str) -> JobDocument | None:
    return next((doc for doc in job.documents if doc.kind == kind), None)


def load(job: Job, kind: str, schema: type[T]) -> T | None:
    doc = _find(job, kind)
    return schema.model_validate(doc.data) if doc is not None and doc.data else None


def store(db: Session, job: Job, kind: str, value: BaseModel) -> None:
    data: dict[str, Any] = value.model_dump(mode="json")
    doc = _find(job, kind)
    if doc is None:
        job.documents.append(JobDocument(kind=kind, data=data))
    else:
        doc.data = data
        doc.updated_at = datetime.now(timezone.utc)
    db.commit()


def all_cover_letters(job: Job) -> dict[str, CoverLetter]:
    letters = {tone: load(job, cover_letter_kind(tone), CoverLetter) for tone in TONES}
    return {tone: letter for tone, letter in letters.items() if letter is not None}


def _context(db: Session, llm: LLMProvider, job: Job, max_retries: int) -> tuple[ProfileData, str, MatchResult]:
    """Profile, its fingerprint, and a match for the current profile (scored on demand)."""
    profile = require_profile(db)
    data = ProfileData.model_validate(profile)
    match, _ = score_or_reuse(db, llm, job, max_retries=max_retries)
    return data, profile_fingerprint(data), match


# ---------- tailoring ----------


def tailoring_or_reuse(
    db: Session, llm: LLMProvider, job: Job, *, max_retries: int, regenerate: bool = False
) -> tuple[TailoringResult, bool]:
    profile, fingerprint, match = _context(db, llm, job, max_retries)
    existing = load(job, TAILORING, TailoringResult)
    if existing is not None and existing.profile_fingerprint == fingerprint and not regenerate:
        return existing, True
    result = tailor_bullets(llm, profile, JobRequirements.model_validate(job), match, fingerprint=fingerprint, max_retries=max_retries)
    store(db, job, TAILORING, result)
    return result, False


def set_bullet_decisions(
    db: Session, job: Job, decisions: dict[str, BulletStatus], edits: dict[str, str] | None = None
) -> TailoringResult:
    """Apply accept/reject decisions and the user's own edits (the user is the source of truth for their wording)."""
    edits = edits or {}
    tailoring = load(job, TAILORING, TailoringResult)
    if tailoring is None:
        raise NotFoundError("Tailor your bullets for this job first.")
    known = {b.id for b in tailoring.bullets}
    unknown = sorted((set(decisions) | set(edits)) - known)
    if unknown:
        raise AppError(f"Unknown bullet id(s): {', '.join(unknown)}.", status_code=422)
    bullets = []
    for bullet in tailoring.bullets:
        if bullet.id in edits:
            bullets.append(bullet.model_copy(update={"tailored": edits[bullet.id].strip(), "status": "accepted", "guard_note": ""}))
        else:
            bullets.append(bullet.model_copy(update={"status": decisions.get(bullet.id, bullet.status)}))
    tailoring = tailoring.model_copy(update={"bullets": bullets})
    store(db, job, TAILORING, tailoring)
    return tailoring


# ---------- cover letters ----------


def cover_letter_or_reuse(
    db: Session, llm: LLMProvider, job: Job, *, tone: Tone, max_retries: int, regenerate: bool = False
) -> tuple[CoverLetter, bool]:
    profile, fingerprint, match = _context(db, llm, job, max_retries)
    existing = load(job, cover_letter_kind(tone), CoverLetter)
    # A letter the user edited is never overwritten unless they ask to regenerate.
    if existing is not None and not regenerate and (existing.edited or existing.profile_fingerprint == fingerprint):
        return existing, True
    letter = write_cover_letter(
        llm, profile, JobRequirements.model_validate(job), match, tone=tone, fingerprint=fingerprint, max_retries=max_retries
    )
    store(db, job, cover_letter_kind(tone), letter)
    return letter, False


def update_cover_letter(db: Session, job: Job, *, tone: Tone, body: str) -> CoverLetter:
    existing = load(job, cover_letter_kind(tone), CoverLetter)
    if existing is None:
        raise NotFoundError(f"There is no {tone} cover letter for this job yet.")
    profile = ProfileData.model_validate(require_profile(db))
    match = get_match(job)
    missing = (match.missing_required + match.missing_nice) if match else []
    letter = existing.model_copy(
        update={
            "body": body,
            "edited": True,
            "updated_at": datetime.now(timezone.utc),
            "warnings": letter_warnings(body, profile_text(profile), missing),
        }
    )
    store(db, job, cover_letter_kind(tone), letter)
    return letter


# ---------- interview prep ----------


def interview_prep_or_reuse(
    db: Session, llm: LLMProvider, job: Job, *, max_retries: int, regenerate: bool = False
) -> tuple[InterviewPrep, bool]:
    profile = ProfileData.model_validate(require_profile(db))
    fingerprint = profile_fingerprint(profile)
    existing = load(job, INTERVIEW, InterviewPrep)
    if existing is not None and existing.profile_fingerprint == fingerprint and not regenerate:
        return existing, True
    prep = generate_interview_questions(
        llm, profile, JobRequirements.model_validate(job), get_match(job), fingerprint=fingerprint, max_retries=max_retries
    )
    store(db, job, INTERVIEW, prep)
    return prep, False
