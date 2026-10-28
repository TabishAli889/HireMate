"""Job analysis and match schemas. `JobRequirements`, `SemanticMatches` and `MatchNarrative` are LLM contracts."""

from typing import Annotated, Literal

from pydantic import Field, HttpUrl, model_validator

from app.schemas.application import ApplicationBrief, ApplicationStatus
from app.schemas.common import UTCDateTime
from app.schemas.documents import CoverLetter, InterviewPrep, TailoringResult
from app.schemas.profile import CleanBullets, CleanTags, LongText, Schema, ShortText

Seniority = Literal["internship", "entry", "mid", "senior", "unknown"]


# ---------- Job posting ----------


class JobRequirements(Schema):
    """What the posting asks for. Every field defaults to empty so nothing is invented."""

    title: ShortText = ""
    company: ShortText = ""
    location: ShortText = ""
    employment_type: ShortText = Field(default="", description="e.g. Full-time, Internship, Remote, Hybrid.")
    seniority: Seniority = "unknown"
    required_skills: CleanTags = Field(default_factory=list, description="Concrete skills/tools the posting requires.")
    nice_to_have_skills: CleanTags = Field(default_factory=list, description="Skills marked preferred, bonus or nice to have.")
    responsibilities: CleanBullets = Field(default_factory=list, description="Up to 10 key duties.")
    summary: LongText = Field(default="", description="One or two plain sentences describing the role.")


class JobAnalyzeRequest(Schema):
    """Body of POST /jobs/analyze: exactly one of `text` or `url`."""

    text: Annotated[str, Field(max_length=30_000)] | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "JobAnalyzeRequest":
        has_text = bool(self.text and self.text.strip())
        if has_text == (self.url is not None):
            raise ValueError("Provide either the job posting text or a job URL (not both).")
        if has_text and len(self.text.strip()) < 80:  # type: ignore[union-attr]
            raise ValueError("That posting is too short. Paste the full job description.")
        return self


# ---------- Matching ----------


class SkillMatch(Schema):
    skill: ShortText
    evidence: Annotated[str, Field(max_length=400)] = Field(description="Where the profile shows this skill.")
    direct: bool = Field(default=True, description="False when matched via related experience (verified quote).")


class MatchBreakdown(Schema):
    required_matched: int
    required_total: int
    nice_matched: int
    nice_total: int
    seniority: Seniority
    seniority_fit: float = Field(ge=0, le=1)


class GapItem(Schema):
    skill: ShortText
    priority: int = Field(default=1, ge=1, le=50)
    why: LongText = Field(default="", description="Why this skill matters for this job, one sentence.")
    first_steps: CleanBullets = Field(default_factory=list, description="2-3 concrete first steps.")
    estimated_time: ShortText = Field(default="", description="Realistic time to basic proficiency, e.g. '1-2 weeks'.")


class SemanticCandidate(Schema):
    skill: ShortText
    evidence_quote: Annotated[str, Field(max_length=300)] = Field(description="Exact quote copied from the profile.")


class SemanticMatches(Schema):
    """LLM output: job skills the profile demonstrates indirectly, each backed by a verbatim quote."""

    matches: Annotated[list[SemanticCandidate], Field(max_length=60)] = Field(default_factory=list)


class MatchExplanation(Schema):
    """LLM output: plain-language explanation of an already-computed score."""

    explanation: Annotated[str, Field(min_length=20, max_length=1500)]


class GapPlan(Schema):
    """LLM output: ordered learning plan for missing skills."""

    gap_plan: Annotated[list[GapItem], Field(max_length=8)] = Field(default_factory=list)


class MatchResult(Schema):
    score: Annotated[int, Field(ge=0, le=100)]
    matched_skills: list[SkillMatch]
    missing_required: list[str]
    missing_nice: list[str]
    breakdown: MatchBreakdown
    explanation: str
    gap_plan: list[GapItem]
    profile_updated_at: UTCDateTime
    scored_at: UTCDateTime
    # Hash of the profile content this score was computed from. Same profile + same job = reuse the score.
    profile_fingerprint: str = ""


# ---------- API responses ----------


class JobOut(JobRequirements):
    id: int
    source_url: str | None
    created_at: UTCDateTime
    match: MatchResult | None = None
    tailoring: TailoringResult | None = None
    cover_letters: dict[str, CoverLetter] = Field(default_factory=dict)
    interview_prep: InterviewPrep | None = None
    application: ApplicationBrief | None = None


class JobSummary(Schema):
    id: int
    title: str
    company: str
    seniority: Seniority
    match_score: int | None
    created_at: UTCDateTime
    has_tailoring: bool = False
    has_cover_letter: bool = False
    has_interview_prep: bool = False
    application_status: ApplicationStatus | None = None
