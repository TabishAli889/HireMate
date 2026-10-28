"""LLM failure modes, each with a friendly message and the right HTTP status."""

from app.core.exceptions import AppError


class LLMNotConfiguredError(AppError):
    status_code = 503
    default_detail = "The AI isn't configured yet. Add GROQ_API_KEY to backend/.env and restart the API."


class LLMRateLimitError(AppError):
    status_code = 429
    default_detail = "The AI is busy right now (rate limit reached). Please wait a minute and try again."


class LLMUnavailableError(AppError):
    status_code = 503
    default_detail = "The AI service is unreachable right now. Please try again shortly."


class LLMOutputError(AppError):
    status_code = 502
    default_detail = "The AI returned an unexpected format, even after retrying. Please try again."


class LLMToolCallError(LLMOutputError):
    default_detail = "The AI produced an invalid tool call."

    def __init__(self, detail: str | None = None, *, failed_generation: str = ""):
        super().__init__(detail)
        self.failed_generation = failed_generation
