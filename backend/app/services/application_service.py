"""Application tracker: create cards, move them between columns, edit details, keep a timeline.

Every meaningful change writes a timeline event, so a card shows its own history
("Added to Saved", "Moved from Applied to Interview", "Deadline set to 12 Nov 2026").
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.schemas.application import (
    STATUS_LABELS,
    STATUSES,
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services.job_service import get_job


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_date(value: date) -> str:
    return f"{value.day} {value.strftime('%b %Y')}"


def _log(app: Application, kind: str, message: str) -> None:
    app.events.append(ApplicationEvent(kind=kind, message=message))
    app.updated_at = _now()


def _column(db: Session, status: str, *, exclude: int | None = None) -> list[Application]:
    stmt = select(Application).where(Application.status == status).order_by(Application.position, Application.id)
    return [app for app in db.scalars(stmt).all() if app.id != exclude]


def _renumber(cards: list[Application]) -> None:
    for index, card in enumerate(cards):
        card.position = index


# ---------- reading ----------


def get_application(db: Session, application_id: int) -> Application:
    app = db.get(Application, application_id)
    if app is None:
        raise NotFoundError("That application isn't on your board (it may have been deleted).")
    return app


def list_applications(db: Session) -> list[Application]:
    """Every card, grouped by column order (Saved → Rejected) then position."""
    order = {status: index for index, status in enumerate(STATUSES)}
    cards = db.scalars(select(Application)).all()
    return sorted(cards, key=lambda a: (order.get(a.status, len(order)), a.position, a.id))


def to_out(app: Application) -> ApplicationOut:
    out = ApplicationOut.model_validate(app)
    job = app.job
    if job is None:
        return out
    kinds = {doc.kind for doc in job.documents}
    return out.model_copy(
        update={
            "match_score": job.match_score,
            "has_tailoring": "tailoring" in kinds,
            "has_cover_letter": any(k.startswith("cover_letter:") for k in kinds),
            "has_interview_prep": "interview_prep" in kinds,
        }
    )


# ---------- writing ----------


def create_application(db: Session, body: ApplicationCreate) -> Application:
    job: Job | None = None
    if body.job_id is not None:
        job = get_job(db, body.job_id)
        if job.application is not None:
            raise ConflictError(
                f"This job is already on your board (in {STATUS_LABELS[job.application.status]})."
            )
    app = Application(
        job=job,  # also sets job.application, so the job sees its card right away
        title=body.title or (job.title if job else "") or "Untitled role",
        company=body.company or (job.company if job else ""),
        link=body.link or ((job.source_url or "") if job else ""),
        status=body.status,
        notes=body.notes,
        deadline=body.deadline,
        position=len(_column(db, body.status)),  # bottom of its column
    )
    _log(app, "created", f"Added to {STATUS_LABELS[body.status]}")
    if body.deadline:
        _log(app, "deadline", f"Deadline set to {_fmt_date(body.deadline)}")
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def save_job_to_tracker(db: Session, job: Job) -> tuple[Application, bool]:
    """Idempotent version for the agent: returns (card, created)."""
    if job.application is not None:
        return job.application, False
    return create_application(db, ApplicationCreate(job_id=job.id)), True


def update_application(db: Session, app: Application, body: ApplicationUpdate) -> Application:
    changes = body.model_dump(exclude_unset=True)

    # A blank title is ignored (a card always needs one); company and link may be cleared.
    detail_fields = [
        f for f in ("title", "company", "link") if changes.get(f) is not None and (f != "title" or changes[f])
    ]
    changed_details = [f for f in detail_fields if getattr(app, f) != changes[f]]
    for field in changed_details:
        setattr(app, field, changes[field])
    if changed_details:
        _log(app, "details", f"Updated {', '.join(changed_details)}")

    if "notes" in changes and changes["notes"] is not None and changes["notes"] != app.notes:
        app.notes = changes["notes"]
        _log(app, "notes", "Notes updated" if app.notes else "Notes cleared")

    if "deadline" in changes and changes["deadline"] != app.deadline:
        app.deadline = changes["deadline"]
        _log(app, "deadline", f"Deadline set to {_fmt_date(app.deadline)}" if app.deadline else "Deadline removed")

    db.commit()
    db.refresh(app)
    return app


def move_application(db: Session, app: Application, status: ApplicationStatus, position: int) -> Application:
    """Place the card at `position` in `status`'s column and close the gap it left behind."""
    previous = app.status
    target = _column(db, status, exclude=app.id)
    target.insert(min(position, len(target)), app)
    app.status = status
    _renumber(target)
    if previous != status:
        _renumber(_column(db, previous, exclude=app.id))
        _log(app, "status", f"Moved from {STATUS_LABELS[previous]} to {STATUS_LABELS[status]}")
    else:
        app.updated_at = _now()
    db.commit()
    db.refresh(app)
    return app


def delete_application(db: Session, app: Application) -> None:
    status, app_id = app.status, app.id
    db.delete(app)
    db.flush()
    _renumber(_column(db, status, exclude=app_id))
    db.commit()
