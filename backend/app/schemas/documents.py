"""Schemas for Phase 5 documents. *Draft classes are LLM contracts; the rest are what the API stores and returns."""

from typing import Annotated, Literal

from pydantic import Field

from app.schemas.common import UTCDateTime
from app.schemas.profile import Bullet, LongText, Schema, ShortText

Tone = Literal["professional", "friendly", "confident"]
TONES: tuple[Tone, ...] = ("professional", "friendly", "confident")
BulletStatus = Literal["pending", "accepted", "rejected"]
QuestionCategory = Literal["technical", "behavioral", "project", "role"]

METRIC_PLACEHOLDER = "[add real number]"


# ---------- Tailored bullets ----------


class TailoredBulletDraft(Schema):
    id: Annotated[str, Field(max_length=20)] = Field(description="The bullet id exactly as given, e.g. exp0-b1.")
    rewritten: Bullet = Field(description="The same achievement, reworded for this job. No new facts or numbers.")
    reason: ShortText = Field(default="", description="One short phrase: which job requirement this now highlights.")


class ProjectRankDraft(Schema):
    name: ShortText
    reason: ShortText = ""


class TailoringDraft(Schema):
    bullets: Annotated[list[TailoredBulletDraft], Field(max_length=60)] = Field(default_factory=list)
    project_ranking: Annotated[list[ProjectRankDraft], Field(max_length=30)] = Field(default_factory=list)


class BulletSuggestion(Schema):
    id: str
    section: Literal["experience", "project"]
    context: str  # e.g. "AI Intern at Acme" or "Project: Campus Bot"
    original: str
    tailored: str
    reason: str = ""
    status: BulletStatus = "pending"
    # Set when the honesty guard rejected the AI's rewrite and kept the original.
    guard_note: str = ""

    @property
    def changed(self) -> bool:
        return self.tailored.strip() != self.original.strip()


class RankedProject(Schema):
    name: str
    rank: int
    reason: str = ""


class TailoringResult(Schema):
    bullets: list[BulletSuggestion]
    projects: list[RankedProject]
    generated_at: UTCDateTime
    profile_fingerprint: str = ""


class BulletDecisions(Schema):
    """PATCH /jobs/{id}/tailor body.

    decisions: bullet id -> accepted / rejected / pending.
    edits: bullet id -> the user's own wording (e.g. with "[add real number]" replaced). An edit is accepted.
    """

    decisions: dict[str, BulletStatus] = Field(default_factory=dict)
    edits: dict[str, Annotated[str, Field(min_length=3, max_length=800)]] = Field(default_factory=dict)


# ---------- Cover letters ----------


class CoverLetterDraft(Schema):
    paragraphs: Annotated[list[Annotated[str, Field(max_length=1500)]], Field(min_length=3, max_length=5)]


class CoverLetter(Schema):
    tone: Tone
    body: Annotated[str, Field(max_length=8000)]
    warnings: list[str] = Field(default_factory=list)
    edited: bool = False
    generated_at: UTCDateTime
    updated_at: UTCDateTime
    profile_fingerprint: str = ""


class CoverLetterRequest(Schema):
    tone: Tone = "professional"
    regenerate: bool = False


class CoverLetterUpdate(Schema):
    body: Annotated[str, Field(min_length=20, max_length=8000)]


# ---------- Interview prep ----------


class InterviewQuestionDraft(Schema):
    question: Annotated[str, Field(max_length=400)]
    category: QuestionCategory
    hint: LongText = Field(description="2-3 sentences on how to answer, using the candidate's real projects or experience.")
    project: ShortText = Field(default="", description="Name of the candidate's project the hint draws on, or empty.")


class InterviewPrepDraft(Schema):
    questions: Annotated[list[InterviewQuestionDraft], Field(min_length=6, max_length=10)]


class InterviewQuestion(Schema):
    question: str
    category: QuestionCategory
    hint: str
    project: str = ""


class InterviewPrep(Schema):
    questions: list[InterviewQuestion]
    generated_at: UTCDateTime
    profile_fingerprint: str = ""


class RegenerateRequest(Schema):
    regenerate: bool = False
