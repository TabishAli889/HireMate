"""What the agent knows during one run, and what a tool needs to do its work."""

from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.llm import LLMProvider


@dataclass
class AgentState:
    """Shared 'blackboard' the tools read and write. Large data (posting text) never goes through the LLM."""

    request: str
    url: str | None = None
    posting_text: str | None = None
    job_id: int | None = None
    has_profile: bool = False
    has_match: bool = False  # a match exists on the job (this run or earlier)
    scored: bool = False  # scored during this run
    planned: bool = False  # skill plan written during this run
    tone: str = "professional"  # cover letter tone for this run
    tailored: bool = False
    letter_written: bool = False
    interview_prepared: bool = False
    application_saved: bool = False
    completed: list[str] = field(default_factory=list)


@dataclass
class ToolContext:
    db: Session
    llm: LLMProvider
    state: AgentState
    max_retries: int
    publish_job: Callable[[Job], None]
