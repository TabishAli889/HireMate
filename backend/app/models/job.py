"""Analyzed job postings plus their latest match result."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.profile import utcnow

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.document import JobDocument


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    company: Mapped[str] = mapped_column(String(300), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    employment_type: Mapped[str] = mapped_column(String(300), default="")
    seniority: Mapped[str] = mapped_column(String(20), default="unknown")
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    nice_to_have_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")

    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")

    match_score: Mapped[int | None] = mapped_column(nullable=True)
    match_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    documents: Mapped[list["JobDocument"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )
    # The tracker card for this job, if it was saved to the board.
    application: Mapped["Application | None"] = relationship(back_populates="job", uselist=False, lazy="selectin")
