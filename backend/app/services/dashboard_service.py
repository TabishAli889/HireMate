"""Build the dashboard summary from the board, the analyzed jobs and the profile. Pure reads, no AI."""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.schemas.application import STATUS_LABELS, STATUSES
from app.schemas.dashboard import (
    ActivityItem,
    DashboardOut,
    DashboardStats,
    PipelineStage,
    ScorePoint,
    SkillGap,
    UpcomingDeadline,
)
from app.services.job_service import list_jobs
from app.services.profile_service import get_profile

DEADLINE_WINDOW_DAYS = 14
MAX_DEADLINES = 6
MAX_SKILL_GAPS = 6
MAX_ACTIVITY = 8
RECENT_JOBS = 5
SCORE_HISTORY = 12


def pipeline(cards: list[Application]) -> list[PipelineStage]:
    counts = Counter(card.status for card in cards)
    return [PipelineStage(status=s, label=STATUS_LABELS[s], count=counts.get(s, 0)) for s in STATUSES]


def stats(cards: list[Application], jobs: list[Job]) -> DashboardStats:
    counts = Counter(card.status for card in cards)
    sent = sum(counts[s] for s in ("applied", "interview", "offer", "rejected"))
    interviews = counts["interview"] + counts["offer"]
    scores = [job.match_score for job in jobs if job.match_score is not None]
    return DashboardStats(
        applications=len(cards),
        active=counts["saved"] + counts["applied"] + counts["interview"],
        sent=sent,
        interviews=interviews,
        offers=counts["offer"],
        interview_rate=round(100 * interviews / sent) if sent else None,
        jobs_analyzed=len(jobs),
        jobs_scored=len(scores),
        average_match=round(sum(scores) / len(scores)) if scores else None,
        documents_ready=sum(1 for job in jobs if job.documents),
    )


def upcoming_deadlines(cards: list[Application], today: date) -> list[UpcomingDeadline]:
    """Open applications due within the window, overdue ones included, soonest first."""
    horizon = today + timedelta(days=DEADLINE_WINDOW_DAYS)
    due = [
        card
        for card in cards
        if card.deadline is not None and card.status not in ("offer", "rejected") and card.deadline <= horizon
    ]
    due.sort(key=lambda card: (card.deadline, card.id))
    return [
        UpcomingDeadline(
            application_id=card.id, title=card.title, company=card.company, status=card.status, deadline=card.deadline
        )
        for card in due[:MAX_DEADLINES]
        if card.deadline is not None
    ]


def skill_gaps(jobs: list[Job]) -> list[SkillGap]:
    """Required skills you're missing, counted across scored jobs (case-insensitive, first spelling kept)."""
    counts: Counter[str] = Counter()
    spelling: dict[str, str] = {}
    for job in jobs:
        missing = (job.match_result or {}).get("missing_required", [])
        seen: set[str] = set()
        for skill in missing:
            key = skill.casefold()
            if key in seen:  # count each skill once per job
                continue
            seen.add(key)
            spelling.setdefault(key, skill)
            counts[key] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], spelling[item[0]].casefold()))
    return [SkillGap(skill=spelling[key], jobs=n) for key, n in ranked[:MAX_SKILL_GAPS]]


def score_history(jobs: list[Job]) -> list[ScorePoint]:
    """The most recent scored jobs, oldest first (jobs arrive newest first)."""
    scored = [job for job in jobs if job.match_score is not None][:SCORE_HISTORY]
    return [
        ScorePoint(job_id=job.id, title=job.title or "Untitled role", company=job.company, score=job.match_score or 0, created_at=job.created_at)
        for job in reversed(scored)
    ]


def activity(db: Session, jobs: list[Job]) -> list[ActivityItem]:
    """Latest timeline events and job analyses, newest first."""
    stmt = select(ApplicationEvent).order_by(ApplicationEvent.created_at.desc(), ApplicationEvent.id.desc()).limit(MAX_ACTIVITY)
    items = [
        ActivityItem(
            kind=event.kind,
            message=event.message,
            title=event.application.title,
            company=event.application.company,
            created_at=event.created_at,
            application_id=event.application_id,
            job_id=event.application.job_id,
        )
        for event in db.scalars(stmt).all()
    ]
    items += [
        ActivityItem(
            kind="analyzed",
            message=f"Analyzed · match {job.match_score}%" if job.match_score is not None else "Analyzed",
            title=job.title or "Untitled role",
            company=job.company,
            created_at=job.created_at,
            job_id=job.id,
        )
        for job in jobs[:MAX_ACTIVITY]
    ]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return items[:MAX_ACTIVITY]


def build_dashboard(db: Session, today: date | None = None) -> DashboardOut:
    cards = list(db.scalars(select(Application)).all())
    jobs = list(db.scalars(select(Job).order_by(Job.created_at.desc(), Job.id.desc())).all())
    profile = get_profile(db)
    return DashboardOut(
        profile_name=profile.full_name if profile else "",
        has_profile=profile is not None,
        stats=stats(cards, jobs),
        pipeline=pipeline(cards),
        deadlines=upcoming_deadlines(cards, today or date.today()),
        skill_gaps=skill_gaps(jobs),
        score_history=score_history(jobs),
        recent_jobs=list_jobs(db, RECENT_JOBS),
        activity=activity(db, jobs),
    )
