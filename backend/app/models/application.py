"""Application tracker: one card per job application, plus a timeline of what happened to it.

New tables (not new columns), so existing databases upgrade with `create_all` and no migration.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.profile import utcnow

if TYPE_CHECKING:
    from app.models.job import Job


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Optional: you can also track jobs you never analyzed. One card per analyzed job.
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), default="")
    company: Mapped[str] = mapped_column(String(300), default="")
    link: Mapped[str] = mapped_column(String(2000), default="")
    # saved | applied | interview | offer | rejected
    status: Mapped[str] = mapped_column(String(20), default="saved", index=True)
    # Order inside its column (0 = top).
    position: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["Job | None"] = relationship(back_populates="application", lazy="selectin")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApplicationEvent.id",
    )


class ApplicationEvent(Base):
    """One line in an application's timeline ("Moved from Saved to Applied")."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    # created | status | deadline | notes | details
    kind: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="events")
