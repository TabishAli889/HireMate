"""Job persistence plus the building blocks the endpoints and the agent tools share.

Consistency rules (so the score only moves when something real changes):
- The same posting text is never re-extracted: the saved job and its requirements are reused.
- A job is only re-scored when the profile content changed (compared by fingerprint).
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.models.job import Job
from app.models.profile import Profile
from app.schemas.job import JobOut, JobRequirements, JobSummary, MatchResult
from app.schemas.profile import ProfileData
from app.services import job_scraper
from app.services.job_analyzer import extract_job_requirements
from app.services.llm import LLMProvider
from app.services.match_scorer import plan_skill_gaps, score_match
from app.services.profile_service import get_profile

MAX_STORED_TEXT = 20_000


class NotAJobPostingError(AppError):
    status_code = 422
    default_detail = "That doesn't look like a job posting. Please paste the full job description."


class ProfileRequiredError(AppError):
    status_code = 409
    default_detail = "Build your Profile Vault first: upload your resume, then score this job."


def get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("That job analysis doesn't exist (it may have been deleted).")
    return job


def require_profile(db: Session) -> Profile:
    profile = get_profile(db)
    if profile is None:
        raise ProfileRequiredError()
    return profile


def list_jobs(db: Session, limit: int = 20) -> list[JobSummary]:
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc(), Job.id.desc()).limit(limit)).all()
    summaries = []
    for job in jobs:
        kinds = {doc.kind for doc in job.documents}
        summaries.append(
            JobSummary.model_validate(job).model_copy(
                update={
                    "has_tailoring": "tailoring" in kinds,
                    "has_cover_letter": any(k.startswith("cover_letter:") for k in kinds),
                    "has_interview_prep": "interview_prep" in kinds,
                    "application_status": job.application.status if getattr(job, "application", None) else None,
                }
            )
        )
    return summaries


def job_to_out(job: Job) -> JobOut:
    from app.schemas.application import ApplicationBrief
    from app.schemas.documents import InterviewPrep, TailoringResult
    from app.services.document_service import INTERVIEW, TAILORING, all_cover_letters, load

    data = JobRequirements.model_validate(job).model_dump()
    match = MatchResult.model_validate(job.match_result) if job.match_result else None
    return JobOut(
        **data,
        id=job.id,
        source_url=job.source_url,
        created_at=job.created_at,
        match=match,
        tailoring=load(job, TAILORING, TailoringResult),
        cover_letters=all_cover_letters(job),
        interview_prep=load(job, INTERVIEW, InterviewPrep),
        application=ApplicationBrief.model_validate(job.application) if getattr(job, "application", None) else None,
    )


def profile_fingerprint(profile: ProfileData) -> str:
    """Stable hash of everything the matcher can see in the profile."""
    return hashlib.sha256(profile.model_dump_json().encode()).hexdigest()[:16]


def find_job_by_posting(db: Session, posting: str) -> Job | None:
    """An earlier analysis of exactly this posting text, if any."""
    stmt = select(Job).where(Job.raw_text == posting[:MAX_STORED_TEXT]).order_by(Job.id.desc()).limit(1)
    return db.scalars(stmt).first()


def get_match(job: Job) -> MatchResult | None:
    return MatchResult.model_validate(job.match_result) if job.match_result else None


def create_job(db: Session, requirements: JobRequirements, *, posting: str, url: str | None) -> Job:
    """Save extracted requirements as a new job (rejects text that isn't a job posting)."""
    if not requirements.title and not requirements.required_skills and not requirements.nice_to_have_skills:
        raise NotAJobPostingError()
    job = Job(**requirements.model_dump(), source_url=url, raw_text=posting[:MAX_STORED_TEXT])
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def save_match(db: Session, job: Job, result: MatchResult) -> None:
    job.match_score = result.score
    job.match_result = result.model_dump(mode="json")
    job.matched_at = result.scored_at
    db.commit()


def extract_or_reuse(db: Session, llm: LLMProvider, posting: str, *, url: str | None, max_retries: int) -> tuple[Job, bool]:
    """Saved job for this posting. Returns (job, reused): identical text reuses the earlier extraction."""
    existing = find_job_by_posting(db, posting)
    if existing is not None:
        return existing, True
    requirements = extract_job_requirements(llm, posting, max_retries=max_retries)
    return create_job(db, requirements, posting=posting, url=url), False


def score_or_reuse(db: Session, llm: LLMProvider, job: Job, *, max_retries: int) -> tuple[MatchResult, bool]:
    """Match for the current profile. Returns (match, reused): unchanged profile keeps the saved score."""
    profile = require_profile(db)
    profile_data = ProfileData.model_validate(profile)
    fingerprint = profile_fingerprint(profile_data)
    existing = get_match(job)
    if existing is not None and existing.profile_fingerprint == fingerprint:
        return existing, True

    result = score_match(
        llm, profile_data, JobRequirements.model_validate(job), profile_updated_at=profile.updated_at, max_retries=max_retries
    )
    result = result.model_copy(update={"profile_fingerprint": fingerprint})
    save_match(db, job, result)
    return result, False


def plan_or_reuse(db: Session, llm: LLMProvider, job: Job, *, max_retries: int) -> tuple[MatchResult, bool]:
    """Write the skill plan for the job's match unless it already has one (or nothing is missing)."""
    match = get_match(job)
    if match is None:
        raise AppError("Score the match before planning skill gaps.", status_code=409)
    if match.gap_plan or not (match.missing_required or match.missing_nice):
        return match, True
    profile = require_profile(db)
    plan = plan_skill_gaps(
        llm, ProfileData.model_validate(profile), JobRequirements.model_validate(job), match, max_retries=max_retries
    )
    match = match.model_copy(update={"gap_plan": plan})
    save_match(db, job, match)
    return match, False


def analyze_job(db: Session, llm: LLMProvider, *, text: str | None, url: str | None, max_retries: int) -> Job:
    """Read the posting (scraping the URL if given), extract requirements, save the job (or reuse it)."""
    posting = job_scraper.scrape_job_url(url) if url else (text or "").strip()
    job, _ = extract_or_reuse(db, llm, posting, url=url, max_retries=max_retries)
    return job


def score_job(db: Session, llm: LLMProvider, job_id: int, *, max_retries: int) -> MatchResult:
    """Score the saved job against the current profile and plan skill gaps (reusing whatever is still valid)."""
    job = get_job(db, job_id)
    score_or_reuse(db, llm, job, max_retries=max_retries)
    result, _ = plan_or_reuse(db, llm, job, max_retries=max_retries)
    return result
