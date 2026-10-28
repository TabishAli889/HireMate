"""Dashboard summary: one request for everything the home page shows."""

from datetime import date

from pydantic import Field

from app.schemas.application import ApplicationStatus
from app.schemas.common import UTCDateTime
from app.schemas.job import JobSummary
from app.schemas.profile import Schema


class DashboardStats(Schema):
    applications: int = 0
    active: int = Field(default=0, description="Saved, Applied or Interview.")
    sent: int = Field(default=0, description="Cards past Saved (Applied, Interview, Offer, Rejected).")
    interviews: int = Field(default=0, description="Cards that reached Interview or Offer.")
    offers: int = 0
    interview_rate: int | None = Field(default=None, description="interviews / sent, as a percentage.")
    jobs_analyzed: int = 0
    jobs_scored: int = 0
    average_match: int | None = None
    documents_ready: int = Field(default=0, description="Jobs with a tailored resume, cover letter or interview prep.")


class PipelineStage(Schema):
    status: ApplicationStatus
    label: str
    count: int


class UpcomingDeadline(Schema):
    application_id: int
    title: str
    company: str
    status: ApplicationStatus
    deadline: date


class SkillGap(Schema):
    skill: str
    jobs: int = Field(description="How many scored jobs require this skill that your profile lacks.")


class ScorePoint(Schema):
    job_id: int
    title: str
    company: str
    score: int
    created_at: UTCDateTime


class ActivityItem(Schema):
    kind: str  # "analyzed" or a timeline event kind (created, status, deadline, notes, details)
    message: str
    title: str
    company: str
    created_at: UTCDateTime
    application_id: int | None = None
    job_id: int | None = None


class DashboardOut(Schema):
    profile_name: str = ""
    has_profile: bool = False
    stats: DashboardStats
    pipeline: list[PipelineStage]
    deadlines: list[UpcomingDeadline]
    skill_gaps: list[SkillGap]
    score_history: list[ScorePoint] = Field(default_factory=list, description="Last scored jobs, oldest first.")
    recent_jobs: list[JobSummary]
    activity: list[ActivityItem]
