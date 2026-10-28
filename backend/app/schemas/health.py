"""Schema for GET /health."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness info. Reports whether an LLM key is configured, never the key itself."""

    status: Literal["ok"]
    app: str
    version: str
    environment: str
    llm_configured: bool
    llm_model: str
