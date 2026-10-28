"""Phase 6: the application tracker (Kanban board)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.application import ApplicationCreate, ApplicationMove, ApplicationOut, ApplicationUpdate
from app.services import application_service as tracker

router = APIRouter(prefix="/applications", tags=["applications"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: DbSession) -> list[ApplicationOut]:
    """Every card, in column order (Saved → Rejected) and position."""
    return [tracker.to_out(app) for app in tracker.list_applications(db)]


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(body: ApplicationCreate, db: DbSession) -> ApplicationOut:
    """Add an analyzed job (`job_id`) or any other role (title, company, link) to the board."""
    return tracker.to_out(tracker.create_application(db, body))


@router.get("/{application_id}", response_model=ApplicationOut)
def read_application(application_id: int, db: DbSession) -> ApplicationOut:
    return tracker.to_out(tracker.get_application(db, application_id))


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, body: ApplicationUpdate, db: DbSession) -> ApplicationOut:
    """Edit title, company, link, notes or deadline. Changes are added to the timeline."""
    return tracker.to_out(tracker.update_application(db, tracker.get_application(db, application_id), body))


@router.post("/{application_id}/move", response_model=ApplicationOut)
def move_application(application_id: int, body: ApplicationMove, db: DbSession) -> ApplicationOut:
    """Drag and drop: put the card in a column at a position."""
    app = tracker.get_application(db, application_id)
    return tracker.to_out(tracker.move_application(db, app, body.status, body.position))


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_application(application_id: int, db: DbSession) -> Response:
    tracker.delete_application(db, tracker.get_application(db, application_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
