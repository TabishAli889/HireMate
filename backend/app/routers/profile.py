"""Profile Vault endpoints: upload a resume PDF, read and edit the structured profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.rate_limit import upload_limiter
from app.schemas.profile import ProfileData, ProfileOut
from app.services.llm import LLMProvider, get_llm_provider
from app.services.profile_service import get_profile, save_profile
from app.services.resume_parser import extract_pdf_text, parse_resume_text, validate_pdf

router = APIRouter(prefix="/profile", tags=["profile"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ProfileOut)
def read_profile(db: DbSession) -> ProfileOut:
    """Return the saved profile, or 404 if none exists yet."""
    profile = get_profile(db)
    if profile is None:
        raise NotFoundError("No profile yet. Upload your resume to create one.")
    return ProfileOut.model_validate(profile)


@router.put("", response_model=ProfileOut)
def update_profile(data: ProfileData, db: DbSession) -> ProfileOut:
    """Replace the profile with the user's reviewed/edited version. Once edited, it's the user's own (not demo)."""
    return ProfileOut.model_validate(save_profile(db, data, is_demo=False))


@router.post("/upload", response_model=ProfileOut, dependencies=[Depends(upload_limiter)])
def upload_resume(
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMProvider, Depends(get_llm_provider)],
    file: Annotated[UploadFile, File(description="Resume as a text-based PDF, max 5 MB")],
) -> ProfileOut:
    """Validate the PDF, extract its text, structure it with the LLM and save it as the profile."""
    data = file.file.read(settings.max_upload_bytes + 1)
    validate_pdf(file.filename, data, settings.max_upload_bytes)
    text = extract_pdf_text(data)
    parsed = parse_resume_text(llm, text, max_retries=settings.llm_max_retries)
    profile = save_profile(db, parsed, source_filename=file.filename, is_demo=False)
    return ProfileOut.model_validate(profile)
