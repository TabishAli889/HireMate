"""Phase 5 endpoints: tailored bullets, cover letters, interview prep, and PDF exports."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.rate_limit import analysis_limiter
from app.schemas.documents import (
    BulletDecisions,
    CoverLetter,
    CoverLetterRequest,
    CoverLetterUpdate,
    InterviewPrep,
    RegenerateRequest,
    TailoringResult,
    Tone,
)
from app.schemas.profile import ProfileData
from app.services import document_service as docs
from app.services.job_service import get_job, require_profile
from app.services.llm import LLMProvider, get_llm_provider
from app.services.pdf_export import render_letter_pdf, render_resume_pdf
from app.services.tailoring import apply_accepted

router = APIRouter(prefix="/jobs/{job_id}", tags=["documents"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
LLM = Annotated[LLMProvider, Depends(get_llm_provider)]


def _pdf(content: bytes, filename: str) -> Response:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "document"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )


# ---------- tailored bullets ----------


@router.post("/tailor", response_model=TailoringResult, dependencies=[Depends(analysis_limiter)])
def tailor(job_id: int, db: DbSession, settings: AppSettings, llm: LLM, body: RegenerateRequest | None = None) -> TailoringResult:
    """Rewrite the profile's existing bullets for this job (honesty-checked) and rank projects."""
    result, _ = docs.tailoring_or_reuse(
        db, llm, get_job(db, job_id), max_retries=settings.llm_max_retries, regenerate=bool(body and body.regenerate)
    )
    return result


@router.patch("/tailor", response_model=TailoringResult)
def decide_bullets(job_id: int, body: BulletDecisions, db: DbSession) -> TailoringResult:
    """Accept or reject individual rewritten bullets, or save your own wording for one."""
    return docs.set_bullet_decisions(db, get_job(db, job_id), body.decisions, body.edits)


@router.get("/tailor/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def tailored_resume_pdf(job_id: int, db: DbSession) -> Response:
    """Resume PDF with accepted rewrites swapped in and projects in ranked order."""
    job = get_job(db, job_id)
    tailoring = docs.load(job, docs.TAILORING, TailoringResult)
    if tailoring is None:
        raise NotFoundError("Tailor your bullets for this job first.")
    profile = ProfileData.model_validate(require_profile(db))
    pdf = render_resume_pdf(apply_accepted(profile, tailoring))
    return _pdf(pdf, f"{profile.full_name or 'resume'}-{job.company or job.title or 'job'}-resume")


# ---------- cover letters ----------


@router.post("/cover-letter", response_model=CoverLetter, dependencies=[Depends(analysis_limiter)])
def cover_letter(job_id: int, body: CoverLetterRequest, db: DbSession, settings: AppSettings, llm: LLM) -> CoverLetter:
    """Write (or reuse) the cover letter in the chosen tone."""
    letter, _ = docs.cover_letter_or_reuse(
        db, llm, get_job(db, job_id), tone=body.tone, max_retries=settings.llm_max_retries, regenerate=body.regenerate
    )
    return letter


@router.put("/cover-letter/{tone}", response_model=CoverLetter)
def edit_cover_letter(job_id: int, tone: Tone, body: CoverLetterUpdate, db: DbSession) -> CoverLetter:
    """Save the user's edits; honesty warnings are recalculated."""
    return docs.update_cover_letter(db, get_job(db, job_id), tone=tone, body=body.body)


@router.get("/cover-letter/{tone}/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def cover_letter_pdf(job_id: int, tone: Tone, db: DbSession) -> Response:
    job = get_job(db, job_id)
    letter = docs.load(job, docs.cover_letter_kind(tone), CoverLetter)
    if letter is None:
        raise NotFoundError(f"There is no {tone} cover letter for this job yet.")
    profile = ProfileData.model_validate(require_profile(db))
    return _pdf(render_letter_pdf(profile, letter.body), f"{profile.full_name or 'cover'}-{job.company or 'job'}-cover-letter")


# ---------- interview prep ----------


@router.post("/interview-prep", response_model=InterviewPrep, dependencies=[Depends(analysis_limiter)])
def interview_prep(job_id: int, db: DbSession, settings: AppSettings, llm: LLM, body: RegenerateRequest | None = None) -> InterviewPrep:
    """Eight likely questions with answer hints from the user's real projects."""
    prep, _ = docs.interview_prep_or_reuse(
        db, llm, get_job(db, job_id), max_retries=settings.llm_max_retries, regenerate=bool(body and body.regenerate)
    )
    return prep
