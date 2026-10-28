"""Job analysis endpoints: analyze a posting, list/read analyses, score the match."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import analysis_limiter
from app.schemas.job import JobAnalyzeRequest, JobOut, JobSummary, MatchResult
from app.services.job_service import analyze_job, get_job, job_to_out, list_jobs, score_job
from app.services.llm import LLMProvider, get_llm_provider

router = APIRouter(prefix="/jobs", tags=["jobs"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
LLM = Annotated[LLMProvider, Depends(get_llm_provider)]


@router.post("/analyze", response_model=JobOut, dependencies=[Depends(analysis_limiter)])
def analyze(body: JobAnalyzeRequest, db: DbSession, settings: AppSettings, llm: LLM) -> JobOut:
    """Extract title, company, skills, seniority and responsibilities from pasted text or a URL."""
    job = analyze_job(
        db,
        llm,
        text=body.text,
        url=str(body.url) if body.url else None,
        max_retries=settings.llm_max_retries,
    )
    return job_to_out(job)


@router.get("", response_model=list[JobSummary])
def recent_jobs(db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[JobSummary]:
    """Most recent analyses first."""
    return list_jobs(db, limit)


@router.get("/{job_id}", response_model=JobOut)
def read_job(job_id: int, db: DbSession) -> JobOut:
    return job_to_out(get_job(db, job_id))


@router.post("/{job_id}/match", response_model=MatchResult, dependencies=[Depends(analysis_limiter)])
def match(job_id: int, db: DbSession, settings: AppSettings, llm: LLM) -> MatchResult:
    """Score the job against the current profile (0-100) with matched/missing skills and a skill plan."""
    return score_job(db, llm, job_id, max_retries=settings.llm_max_retries)
