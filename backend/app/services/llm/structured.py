"""Validated structured output: every LLM reply must parse into a Pydantic model.

On failure we show the model its own reply plus the validation errors and ask again,
up to `max_retries` times, then fail with a clear LLMOutputError.
"""

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.services.llm.errors import LLMOutputError
from app.services.llm.provider import LLMProvider, Message

logger = logging.getLogger("hiremate.llm")

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_MAX_ERRORS_SHOWN = 8


def strip_code_fences(text: str) -> str:
    """Remove a surrounding ```json ... ``` block if the model added one."""
    match = _FENCE.match(text)
    return match.group(1) if match else text.strip()


def summarize_validation_error(exc: ValidationError) -> str:
    """Short, model-readable list of what was wrong."""
    lines = []
    for err in exc.errors(include_url=False)[:_MAX_ERRORS_SHOWN]:
        location = ".".join(str(part) for part in err["loc"]) or "(root)"
        lines.append(f"- {location}: {err['msg']}")
    return "\n".join(lines)


def build_system_prompt(instructions: str, schema: type[BaseModel]) -> str:
    """Append the JSON Schema contract to task instructions."""
    return (
        f"{instructions.strip()}\n\n"
        "Reply with ONE JSON object that matches this JSON Schema. "
        "No markdown, no code fences, no commentary.\n"
        f"JSON Schema:\n{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
    )


def generate_structured(
    provider: LLMProvider,
    schema: type[T],
    *,
    instructions: str,
    user_content: str,
    max_retries: int = 2,
) -> T:
    """Ask the LLM for JSON matching `schema`; retry with the validation error; raise LLMOutputError if still invalid."""
    messages: list[Message] = [
        {"role": "system", "content": build_system_prompt(instructions, schema)},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(max_retries + 1):
        raw = provider.complete_json(messages)
        try:
            return schema.model_validate_json(strip_code_fences(raw))
        except ValidationError as exc:
            problems = summarize_validation_error(exc)
            logger.warning("Invalid %s from LLM (attempt %d/%d):\n%s", schema.__name__, attempt + 1, max_retries + 1, problems)
            messages = [
                *messages,
                {"role": "assistant", "content": raw or "(empty or malformed JSON)"},
                {
                    "role": "user",
                    "content": f"That reply failed validation:\n{problems}\n"
                    "Return the corrected JSON object only, following the schema exactly.",
                },
            ]

    raise LLMOutputError()
