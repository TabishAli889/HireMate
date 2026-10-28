"""Profile schemas. `ProfileData` is BOTH the LLM extraction contract and the PUT /profile body."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _clean_list(items: list[str]) -> list[str]:
    """Strip items, drop blanks and case-insensitive duplicates, keep original order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        value = " ".join(item.split())
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            cleaned.append(value)
    return cleaned


ShortText = Annotated[str, Field(max_length=300)]
LongText = Annotated[str, Field(max_length=3000)]
Bullet = Annotated[str, Field(max_length=800)]
CleanTags = Annotated[list[Annotated[str, Field(max_length=100)]], AfterValidator(_clean_list), Field(max_length=150)]
CleanBullets = Annotated[list[Bullet], AfterValidator(_clean_list), Field(max_length=25)]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EducationItem(Schema):
    institution: ShortText = ""
    degree: ShortText = ""
    field_of_study: ShortText = ""
    start_date: Annotated[str, Field(max_length=60)] = ""
    end_date: Annotated[str, Field(max_length=60)] = ""
    details: LongText = Field(default="", description="Grades, coursework or honours exactly as written.")


class ExperienceItem(Schema):
    company: ShortText = ""
    title: ShortText = ""
    location: ShortText = ""
    start_date: Annotated[str, Field(max_length=60)] = ""
    end_date: Annotated[str, Field(max_length=60)] = Field(default="", description="As written, e.g. 'Present'.")
    bullets: CleanBullets = Field(default_factory=list, description="Achievement bullets, copied near-verbatim.")


class ProjectItem(Schema):
    name: ShortText = ""
    description: LongText = ""
    tech_stack: CleanTags = Field(default_factory=list)
    bullets: CleanBullets = Field(default_factory=list)
    link: Annotated[str, Field(max_length=500)] = ""


class ProfileData(Schema):
    """Structured resume. Every field defaults to empty so missing info is never invented."""

    full_name: ShortText = ""
    headline: ShortText = Field(default="", description="One-line professional title, only if the resume states one.")
    email: ShortText = ""
    phone: Annotated[str, Field(max_length=60)] = ""
    location: ShortText = ""
    links: CleanTags = Field(default_factory=list, description="Portfolio, GitHub, LinkedIn URLs.")
    summary: LongText = ""
    skills: CleanTags = Field(default_factory=list, description="Skills and tools explicitly named in the resume.")
    education: Annotated[list[EducationItem], Field(max_length=20)] = Field(default_factory=list)
    experience: Annotated[list[ExperienceItem], Field(max_length=30)] = Field(default_factory=list)
    projects: Annotated[list[ProjectItem], Field(max_length=30)] = Field(default_factory=list)


class ProfileOut(ProfileData):
    """Profile as returned by the API."""

    id: int
    is_demo: bool
    source_filename: str | None
    updated_at: datetime
