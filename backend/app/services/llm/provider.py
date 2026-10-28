"""Provider wrapper: the rest of the app only knows `LLMProvider`.

- `complete_json` returns a JSON string (used for validated structured output).
- `complete_with_tools` returns the assistant's tool calls (used by the agent loop).
Swapping Groq for another model means writing one new subclass.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from app.services.llm.errors import LLMRateLimitError, LLMToolCallError, LLMUnavailableError

logger = logging.getLogger("hiremate.llm")


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


# Agent-loop messages can also carry tool calls and tool results, so they are plain dicts.
ChatMessage = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = ""


@dataclass(frozen=True)
class AssistantTurn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    def as_message(self) -> ChatMessage:
        """OpenAI/Groq-compatible assistant message for the conversation history."""
        message: ChatMessage = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.raw_arguments or json.dumps(call.arguments)},
                }
                for call in self.tool_calls
            ]
        return message


# Set by the agent runner so a rate-limit backoff can be shown to the user as a live notice.
rate_limit_listener: ContextVar[Callable[[float], None] | None] = ContextVar("rate_limit_listener", default=None)


class LLMProvider(ABC):
    """Minimal interface the app depends on."""

    @abstractmethod
    def complete_json(self, messages: list[Message]) -> str:
        """Return the model's reply, asked to be a single JSON object."""

    def complete_with_tools(self, messages: list[ChatMessage], tools: list[dict[str, Any]]) -> AssistantTurn:
        """Return the model's next turn, which must call one of `tools`."""
        raise NotImplementedError(f"{type(self).__name__} does not support tool calling")


class GroqProvider(LLMProvider):
    """Groq chat completions with exponential backoff on rate limits."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        planner_model: str | None = None,
        reasoning_effort: str | None = None,
        planner_reasoning_effort: str | None = None,
        rate_limit_retries: int = 3,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        from groq import Groq

        self._client = Groq(api_key=api_key, max_retries=0, timeout=60.0)
        self._model = model
        self._planner_model = planner_model or model
        self._reasoning_effort = reasoning_effort or None
        self._planner_reasoning_effort = planner_reasoning_effort or self._reasoning_effort
        self._rate_limit_retries = rate_limit_retries
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds
        self._sleep = sleep

    def _create(self, *, reasoning_effort: str | None = None, **kwargs: Any) -> Any:
        """One chat completion, retrying rate limits with backoff. BadRequestError is left to the caller."""
        import groq

        kwargs.setdefault("model", self._model)
        if reasoning_effort and str(kwargs["model"]).startswith("openai/gpt-oss"):
            # Sent via extra_body so it works with any groq SDK version.
            kwargs["extra_body"] = {"reasoning_effort": reasoning_effort}

        for attempt in range(self._rate_limit_retries + 1):
            try:
                return self._client.chat.completions.create(
                    temperature=0,
                    seed=42,  # best-effort reproducibility: same input → (almost always) same output
                    **kwargs,
                )
            except groq.RateLimitError as exc:
                if attempt == self._rate_limit_retries:
                    raise LLMRateLimitError() from exc
                delay = min(self._retry_after(exc) or self._base_delay * (2**attempt), self._max_delay)
                logger.info("Groq rate limit hit; retrying in %.1fs (attempt %d)", delay, attempt + 1)
                listener = rate_limit_listener.get()
                if listener is not None:
                    listener(delay)
                self._sleep(delay)
            except groq.BadRequestError:
                raise
            except (groq.APIConnectionError, groq.APITimeoutError) as exc:
                raise LLMUnavailableError() from exc
            except groq.APIStatusError as exc:
                logger.warning("Groq API error %s", exc.status_code)
                raise LLMUnavailableError() from exc
        raise LLMRateLimitError()  # unreachable, keeps type checkers happy

    def complete_json(self, messages: list[Message]) -> str:
        import groq

        try:
            response = self._create(
                messages=messages, response_format={"type": "json_object"}, reasoning_effort=self._reasoning_effort
            )
        except groq.BadRequestError as exc:
            # JSON mode returns 400 "json_validate_failed" when the model emits broken JSON.
            # Hand back an empty reply so the structured-output retry loop can correct it.
            if "json_validate_failed" in str(exc):
                logger.info("Groq rejected malformed JSON; letting the validator retry")
                return ""
            raise LLMUnavailableError("The AI rejected the request. Please try again.") from exc
        return response.choices[0].message.content or ""

    def complete_with_tools(self, messages: list[ChatMessage], tools: list[dict[str, Any]]) -> AssistantTurn:
        import groq

        try:
            response = self._create(
                model=self._planner_model,
                messages=messages,
                tools=tools,
                tool_choice="required",
                parallel_tool_calls=False,
                reasoning_effort=self._planner_reasoning_effort,
            )
        except groq.BadRequestError as exc:
            if "tool_use_failed" in str(exc):
                failed = self._failed_generation(exc)
                logger.warning("Groq rejected the planner's tool call (tool_use_failed). Model output: %.300s", failed)
                raise LLMToolCallError(failed_generation=failed) from exc
            raise LLMUnavailableError("The AI rejected the request. Please try again.") from exc

        message = response.choices[0].message
        calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            raw = call.function.arguments or ""
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {}
            calls.append(
                ToolCall(id=call.id, name=call.function.name, arguments=parsed if isinstance(parsed, dict) else {}, raw_arguments=raw)
            )
        return AssistantTurn(content=message.content or "", tool_calls=calls)

    @staticmethod
    def _failed_generation(exc: Exception) -> str:
        """Groq puts the model's rejected output in error.failed_generation."""
        body = getattr(exc, "body", None)
        error = body.get("error", body) if isinstance(body, dict) else None
        value = error.get("failed_generation") if isinstance(error, dict) else None
        return str(value or "")[:2000]

    @staticmethod
    def _retry_after(exc: Exception) -> float | None:
        response = getattr(exc, "response", None)
        value = response.headers.get("retry-after") if response is not None else None
        try:
            return float(value) if value else None
        except ValueError:
            return None
