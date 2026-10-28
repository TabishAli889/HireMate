"""GroqProvider: rate-limit backoff with live notices, and tool-call parsing (Groq client faked)."""

from types import SimpleNamespace
from typing import Any

import groq
import httpx
import pytest

from app.services.llm.errors import LLMRateLimitError, LLMToolCallError
from app.services.llm.provider import GroqProvider, rate_limit_listener


def _rate_limit_error(retry_after: str | None = None) -> groq.RateLimitError:
    headers = {"retry-after": retry_after} if retry_after else {}
    response = httpx.Response(429, headers=headers, request=httpx.Request("POST", "https://api.groq.com/x"))
    return groq.RateLimitError("rate limited", response=response, body=None)


def _completion(content: str = "", tool_calls: list[Any] | None = None) -> Any:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, outcomes: list[Any]):
        self.outcomes = outcomes
        self.kwargs: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.kwargs.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_provider(
    outcomes: list[Any],
    sleeps: list[float],
    planner_model: str | None = None,
    model: str = "test-model",
    reasoning_effort: str | None = None,
) -> tuple[GroqProvider, FakeCompletions]:
    provider = GroqProvider(
        api_key="test",
        model=model,
        planner_model=planner_model,
        reasoning_effort=reasoning_effort,
        rate_limit_retries=2,
        sleep=sleeps.append,
    )
    completions = FakeCompletions(outcomes)
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))  # type: ignore[assignment]
    return provider, completions


def test_backoff_retries_and_notifies() -> None:
    sleeps: list[float] = []
    notices: list[float] = []
    provider, completions = make_provider([_rate_limit_error(), _rate_limit_error("5"), _completion('{"ok": true}')], sleeps)
    token = rate_limit_listener.set(notices.append)
    try:
        assert provider.complete_json([{"role": "user", "content": "hi"}]) == '{"ok": true}'
    finally:
        rate_limit_listener.reset(token)
    assert sleeps == [2.0, 5.0]  # exponential base, then the server's Retry-After
    assert notices == sleeps
    assert completions.kwargs[0]["temperature"] == 0


def test_gives_up_after_retries() -> None:
    provider, _ = make_provider([_rate_limit_error()] * 3, [])
    with pytest.raises(LLMRateLimitError):
        provider.complete_json([{"role": "user", "content": "hi"}])


def test_tool_calls_are_parsed() -> None:
    tool_call = SimpleNamespace(id="c1", function=SimpleNamespace(name="finish", arguments='{"summary": "done"}'))
    bad_args = SimpleNamespace(id="c2", function=SimpleNamespace(name="score_match", arguments="{not json"))
    provider, completions = make_provider([_completion(tool_calls=[tool_call, bad_args])], [])
    turn = provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])
    assert turn.tool_calls[0].name == "finish"
    assert turn.tool_calls[0].arguments == {"summary": "done"}
    assert turn.tool_calls[1].arguments == {}
    assert completions.kwargs[0]["tool_choice"] == "required"
    assert completions.kwargs[0]["model"] == "test-model"


def test_planner_can_use_a_separate_model() -> None:
    finish = SimpleNamespace(id="c1", function=SimpleNamespace(name="finish", arguments='{"summary": "ok"}'))
    provider, completions = make_provider([_completion(tool_calls=[finish]), _completion('{"a": 1}')], [], planner_model="small")
    provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])
    provider.complete_json([{"role": "user", "content": "go"}])
    assert [kw["model"] for kw in completions.kwargs] == ["small", "test-model"]


def test_tool_use_failed_maps_to_tool_call_error() -> None:
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com/x"))
    error = groq.BadRequestError("Error code: 400 - tool_use_failed", response=response, body=None)
    provider, _ = make_provider([error], [])
    with pytest.raises(LLMToolCallError):
        provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])


def test_reasoning_effort_only_sent_to_gpt_oss() -> None:
    finish = SimpleNamespace(id="c1", function=SimpleNamespace(name="finish", arguments="{}"))
    provider, completions = make_provider(
        [_completion('{"a": 1}'), _completion(tool_calls=[finish])],
        [],
        model="openai/gpt-oss-120b",
        planner_model="other/model",
        reasoning_effort="low",
    )
    provider.complete_json([{"role": "user", "content": "go"}])
    provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])
    assert completions.kwargs[0]["extra_body"] == {"reasoning_effort": "low"}
    assert "extra_body" not in completions.kwargs[1]


def test_planner_gets_its_own_reasoning_effort() -> None:
    finish = SimpleNamespace(id="c1", function=SimpleNamespace(name="finish", arguments="{}"))
    sleeps: list[float] = []
    provider = GroqProvider(
        api_key="test",
        model="openai/gpt-oss-120b",
        planner_model="openai/gpt-oss-20b",
        reasoning_effort="low",
        planner_reasoning_effort="medium",
        sleep=sleeps.append,
    )
    completions = FakeCompletions([_completion(tool_calls=[finish])])
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))  # type: ignore[assignment]
    provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])
    assert completions.kwargs[0]["model"] == "openai/gpt-oss-20b"
    assert completions.kwargs[0]["extra_body"] == {"reasoning_effort": "medium"}


def test_failed_generation_is_kept_for_recovery() -> None:
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com/x"))
    body = {"error": {"code": "tool_use_failed", "failed_generation": "to=functions.score_match"}}
    error = groq.BadRequestError("Error code: 400 - tool_use_failed", response=response, body=body)
    provider, _ = make_provider([error], [])
    with pytest.raises(LLMToolCallError) as info:
        provider.complete_with_tools([{"role": "user", "content": "go"}], tools=[])
    assert info.value.failed_generation == "to=functions.score_match"
