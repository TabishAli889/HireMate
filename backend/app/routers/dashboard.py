"""Phase 7: the dashboard summary."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import DashboardOut
from app.services.dashboard_service import build_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Annotated[Session, Depends(get_db)]) -> DashboardOut:
    """Stats, pipeline, upcoming deadlines, most-missed skills, recent jobs and activity, in one call."""
    return build_dashboard(db)
