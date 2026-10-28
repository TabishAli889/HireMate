"""Profile Vault tables: one Profile with ordered Education, Experience and Project rows."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(300), default="")
    headline: Mapped[str] = mapped_column(String(300), default="")
    email: Mapped[str] = mapped_column(String(300), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    links: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)

    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    education: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="Education.position"
    )
    experience: Mapped[list["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="Experience.position"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="Project.position"
    )


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    institution: Mapped[str] = mapped_column(String(300), default="")
    degree: Mapped[str] = mapped_column(String(300), default="")
    field_of_study: Mapped[str] = mapped_column(String(300), default="")
    start_date: Mapped[str] = mapped_column(String(60), default="")
    end_date: Mapped[str] = mapped_column(String(60), default="")
    details: Mapped[str] = mapped_column(Text, default="")

    profile: Mapped[Profile] = relationship(back_populates="education")


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    company: Mapped[str] = mapped_column(String(300), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    start_date: Mapped[str] = mapped_column(String(60), default="")
    end_date: Mapped[str] = mapped_column(String(60), default="")
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)

    profile: Mapped[Profile] = relationship(back_populates="experience")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    name: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    tech_stack: Mapped[list[str]] = mapped_column(JSON, default=list)
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)
    link: Mapped[str] = mapped_column(String(500), default="")

    profile: Mapped[Profile] = relationship(back_populates="projects")
