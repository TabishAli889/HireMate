"""FastAPI dependency that returns the configured LLM provider."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm.errors import LLMNotConfiguredError
from app.services.llm.provider import GroqProvider, LLMProvider


@lru_cache(maxsize=4)
def _groq(api_key: str, model: str, planner_model: str, reasoning_effort: str, planner_effort: str) -> GroqProvider:
    return GroqProvider(
        api_key=api_key,
        model=model,
        planner_model=planner_model or None,
        reasoning_effort=reasoning_effort or None,
        planner_reasoning_effort=planner_effort or None,
    )


def get_llm_provider(settings: Annotated[Settings, Depends(get_settings)]) -> LLMProvider:
    """Groq provider when GROQ_API_KEY is set; otherwise a friendly 503."""
    if not settings.llm_configured or settings.groq_api_key is None:
        raise LLMNotConfiguredError()
    return _groq(
        settings.groq_api_key.get_secret_value().strip(),
        settings.groq_model.strip(),
        settings.groq_planner_model.strip(),
        settings.groq_reasoning_effort,
        settings.groq_planner_reasoning_effort,
    )
