"""Generated documents attached to a job: tailored bullets, cover letters (one per tone), interview prep.

A separate table (not new columns on `jobs`) so existing databases upgrade with no migration.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.profile import utcnow

if TYPE_CHECKING:
    from app.models.job import Job


class JobDocument(Base):
    __tablename__ = "job_documents"
    __table_args__ = (UniqueConstraint("job_id", "kind", name="uq_job_document_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    # "tailoring", "interview_prep", or "cover_letter:<tone>"
    kind: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["Job"] = relationship(back_populates="documents")
