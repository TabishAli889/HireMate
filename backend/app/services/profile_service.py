"""Persistence for the single-user Profile Vault."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.profile import Education, Experience, Profile, Project, utcnow
from app.schemas.profile import ProfileData

PROFILE_ID = 1  # HireMate is single-user for now; multi-user would key this by user id.

_SCALAR_FIELDS = ("full_name", "headline", "email", "phone", "location", "links", "summary", "skills")


def get_profile(db: Session) -> Profile | None:
    """Load the profile with all child rows, or None if nothing has been saved yet."""
    stmt = (
        select(Profile)
        .where(Profile.id == PROFILE_ID)
        .options(selectinload(Profile.education), selectinload(Profile.experience), selectinload(Profile.projects))
    )
    return db.scalars(stmt).first()


def save_profile(
    db: Session,
    data: ProfileData,
    *,
    source_filename: str | None = None,
    is_demo: bool | None = None,
) -> Profile:
    """Create or fully replace the profile with `data` (child rows are replaced in order)."""
    profile = get_profile(db)
    if profile is None:
        profile = Profile(id=PROFILE_ID)
        db.add(profile)

    for field in _SCALAR_FIELDS:
        setattr(profile, field, getattr(data, field))
    profile.education = [Education(position=i, **item.model_dump()) for i, item in enumerate(data.education)]
    profile.experience = [Experience(position=i, **item.model_dump()) for i, item in enumerate(data.experience)]
    profile.projects = [Project(position=i, **item.model_dump()) for i, item in enumerate(data.projects)]

    if source_filename is not None:
        profile.source_filename = source_filename[:255]
    if is_demo is not None:
        profile.is_demo = is_demo
    profile.updated_at = utcnow()

    db.commit()
    return get_profile(db) or profile
