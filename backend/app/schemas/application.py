"""Application tracker schemas."""

from datetime import date
from typing import Annotated, Literal, get_args

from pydantic import AfterValidator, Field, model_validator

from app.schemas.common import UTCDateTime
from app.schemas.profile import Schema, ShortText

ApplicationStatus = Literal["saved", "applied", "interview", "offer", "rejected"]
STATUSES: tuple[ApplicationStatus, ...] = get_args(ApplicationStatus)
STATUS_LABELS: dict[str, str] = {
    "saved": "Saved",
    "applied": "Applied",
    "interview": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
}


def _check_link(value: str) -> str:
    if value and not value.lower().startswith(("http://", "https://")):
        raise ValueError("Links must start with http:// or https://")
    return value


Link = Annotated[str, Field(max_length=2000), AfterValidator(_check_link)]
Notes = Annotated[str, Field(max_length=5000)]


class ApplicationCreate(Schema):
    """Add a card. With `job_id`, title/company/link default to the analyzed job's."""

    job_id: int | None = None
    title: ShortText = ""
    company: ShortText = ""
    link: Link = ""
    status: ApplicationStatus = "saved"
    deadline: date | None = None
    notes: Notes = ""

    @model_validator(mode="after")
    def _needs_a_title(self) -> "ApplicationCreate":
        if self.job_id is None and not self.title:
            raise ValueError("Give the role a title (or pick an analyzed job).")
        return self


class ApplicationUpdate(Schema):
    """Partial update. Send `"deadline": null` to clear the deadline."""

    title: ShortText | None = None
    company: ShortText | None = None
    link: Link | None = None
    notes: Notes | None = None
    deadline: date | None = None


class ApplicationMove(Schema):
    """Drop a card into a column at a position (0 = top). Positions past the end go to the bottom."""

    status: ApplicationStatus
    position: int = Field(default=0, ge=0)


class ApplicationEventOut(Schema):
    id: int
    kind: str
    message: str
    created_at: UTCDateTime


class ApplicationBrief(Schema):
    """What a job page needs to know about its tracker card."""

    id: int
    status: ApplicationStatus


class ApplicationOut(Schema):
    id: int
    job_id: int | None
    title: str
    company: str
    link: str
    status: ApplicationStatus
    position: int
    notes: str
    deadline: date | None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    # From the linked job (empty for manually added cards).
    match_score: int | None = None
    has_tailoring: bool = False
    has_cover_letter: bool = False
    has_interview_prep: bool = False
    events: list[ApplicationEventOut] = Field(default_factory=list)
