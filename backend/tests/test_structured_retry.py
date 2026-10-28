"""Retry logic for validated LLM output."""

import pytest

from app.schemas.profile import ProfileData
from app.services.llm.errors import LLMOutputError
from app.services.llm.structured import generate_structured, strip_code_fences
from tests.conftest import FakeProvider

VALID = '{"full_name": "Sara", "skills": ["Python"]}'


def _run(provider: FakeProvider, max_retries: int = 2) -> ProfileData:
    return generate_structured(provider, ProfileData, instructions="Parse.", user_content="resume", max_retries=max_retries)


def test_valid_first_reply_needs_one_call() -> None:
    provider = FakeProvider([VALID])
    assert _run(provider).full_name == "Sara"
    assert len(provider.calls) == 1


def test_system_prompt_contains_schema() -> None:
    provider = FakeProvider([VALID])
    _run(provider)
    system = provider.calls[0][0]["content"]
    assert "JSON Schema" in system and '"skills"' in system


def test_invalid_then_valid_retries_with_the_error() -> None:
    provider = FakeProvider(['{"skills": "not a list"}', VALID])
    assert _run(provider).skills == ["Python"]
    assert len(provider.calls) == 2
    retry_messages = provider.calls[1]
    assert retry_messages[-2] == {"role": "assistant", "content": '{"skills": "not a list"}'}
    assert "skills" in retry_messages[-1]["content"]
    assert "failed validation" in retry_messages[-1]["content"]


def test_broken_json_is_retried() -> None:
    provider = FakeProvider(['{"full_name": ', VALID])
    assert _run(provider).full_name == "Sara"


def test_empty_reply_is_retried() -> None:
    provider = FakeProvider(["", VALID])
    assert _run(provider).full_name == "Sara"
    assert provider.calls[1][-2]["content"] == "(empty or malformed JSON)"


def test_gives_up_after_max_retries() -> None:
    provider = FakeProvider(["nope", "still nope", "never", VALID])
    with pytest.raises(LLMOutputError):
        _run(provider, max_retries=2)
    assert len(provider.calls) == 3  # first try + 2 retries; the 4th reply is never requested


def test_code_fences_are_stripped() -> None:
    assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_code_fences('  {"a": 1} ') == '{"a": 1}'
    provider = FakeProvider([f"```json\n{VALID}\n```"])
    assert _run(provider).full_name == "Sara"
