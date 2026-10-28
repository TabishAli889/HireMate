"""Request body for POST /agent/run."""

from typing import Annotated, Literal

from pydantic import Field, HttpUrl, model_validator

from app.schemas.profile import Schema


class AgentRunRequest(Schema):
    """What the user wants, plus exactly one input: posting text, a job URL, or an already-saved job."""

    request: Annotated[str, Field(min_length=3, max_length=500)] = "Analyze this job"
    text: Annotated[str, Field(max_length=30_000)] | None = None
    url: HttpUrl | None = None
    job_id: int | None = None
    tone: Literal["professional", "friendly", "confident"] = "professional"

    @model_validator(mode="after")
    def _exactly_one_input(self) -> "AgentRunRequest":
        has_text = bool(self.text and self.text.strip())
        provided = sum([has_text, self.url is not None, self.job_id is not None])
        if provided != 1:
            raise ValueError("Provide exactly one of: the job posting text, a job URL, or a saved job.")
        if has_text and len(self.text.strip()) < 80:  # type: ignore[union-attr]
            raise ValueError("That posting is too short. Paste the full job description.")
        return self
