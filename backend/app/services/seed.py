"""Demo data so a fresh install looks alive. Clearly marked `is_demo` and replaced on first upload."""

import logging

from sqlalchemy.orm import Session

from app.schemas.profile import EducationItem, ExperienceItem, ProfileData, ProjectItem
from app.services.profile_service import get_profile, save_profile

logger = logging.getLogger("hiremate.seed")

DEMO_PROFILE = ProfileData(
    full_name="Ayesha Khan",
    headline="Computer Science student · AI & full-stack developer",
    email="ayesha.demo@example.com",
    phone="",
    location="Lahore, Pakistan",
    links=["https://github.com/ayesha-demo", "https://linkedin.com/in/ayesha-demo"],
    summary=(
        "Final-year BSCS student who builds practical AI apps with Python, FastAPI and Next.js. "
        "Enjoys turning messy data into simple tools people actually use."
    ),
    skills=[
        "Python", "FastAPI", "LangChain", "RAG", "Next.js", "React", "TypeScript",
        "Tailwind CSS", "SQL", "PostgreSQL", "Git", "Docker",
    ],
    education=[
        EducationItem(
            institution="University of the Punjab",
            degree="BS Computer Science",
            start_date="2022",
            end_date="2026",
            details="Relevant coursework: Machine Learning, Databases, Software Engineering",
        )
    ],
    experience=[
        ExperienceItem(
            company="Demo Tech Solutions",
            title="AI Intern",
            location="Lahore",
            start_date="Jul 2025",
            end_date="Sep 2025",
            bullets=[
                "Built a RAG chatbot over company documents using LangChain and FastAPI",
                "Wrote a document ingestion pipeline that chunks and embeds PDFs",
                "Deployed the chatbot backend on Render and the UI on Vercel",
            ],
        )
    ],
    projects=[
        ProjectItem(
            name="Campus Helpdesk Bot",
            description="Answers student questions about admissions and fees from official PDFs.",
            tech_stack=["Python", "LangChain", "FastAPI", "Next.js"],
            bullets=["Implemented retrieval with source citations", "Added a feedback button to flag wrong answers"],
        ),
        ProjectItem(
            name="Expense Splitter",
            description="Web app for splitting shared expenses between roommates.",
            tech_stack=["React", "TypeScript", "PostgreSQL"],
            bullets=["Designed the database schema and REST API", "Built a responsive dashboard with charts"],
        ),
    ],
)


def seed_demo_profile(db: Session, *, force: bool = False) -> bool:
    """Insert the demo profile if no profile exists (or always, with force). Returns True if written."""
    if get_profile(db) is not None and not force:
        return False
    save_profile(db, DEMO_PROFILE, source_filename=None, is_demo=True)
    logger.info("Seeded demo profile")
    return True


def remove_demo_profile(db: Session) -> bool:
    """Delete the profile only if it is the demo one. Real (uploaded or edited) profiles are never touched."""
    profile = get_profile(db)
    if profile is None or not profile.is_demo:
        return False
    db.delete(profile)
    db.commit()
    logger.info("Removed demo profile")
    return True
