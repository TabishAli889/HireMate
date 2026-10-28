"""Shared test setup: in-memory SQLite, no demo seed, no real LLM calls."""

import os

# Must be set before `app` is imported so the engine and settings pick them up.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["GROQ_API_KEY"] = ""
# Ignore any API_KEY / production settings from a local .env: tests call the app directly.
os.environ["API_KEY"] = ""
os.environ["ENVIRONMENT"] = "test"
os.environ["LLM_MAX_RETRIES"] = "2"
os.environ["MAX_UPLOAD_MB"] = "5"
os.environ["UPLOAD_RATE_LIMIT_PER_MINUTE"] = "5"
os.environ["ANALYSIS_RATE_LIMIT_PER_MINUTE"] = "10"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models as _models  # noqa: E402, F401  (registers tables; `as` avoids shadowing `app`)
from app.core.database import Base, engine  # noqa: E402
from app.core.rate_limit import analysis_limiter, upload_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.services.llm import get_llm_provider  # noqa: E402
from app.services.llm.provider import AssistantTurn, ChatMessage, LLMProvider, Message, ToolCall  # noqa: E402


class FakeProvider(LLMProvider):
    """Returns queued replies in order and records every call's messages.

    `replies` feed complete_json; `turns` feed complete_with_tools. A queued Exception is raised instead.
    """

    def __init__(self, replies: list[str | Exception], turns: list[AssistantTurn | Exception] | None = None):
        self.replies = list(replies)
        self.turns = list(turns or [])
        self.calls: list[list[Message]] = []
        self.tool_calls: list[list[ChatMessage]] = []

    def complete_json(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def complete_with_tools(self, messages: list[ChatMessage], tools: list[dict]) -> AssistantTurn:
        self.tool_calls.append(list(messages))
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def call(name: str, **arguments: str) -> AssistantTurn:
    """An assistant turn that calls one tool."""
    return AssistantTurn(content="", tool_calls=[ToolCall(id=f"call_{name}", name=name, arguments=arguments)])


def use_fake_llm(*replies: str, turns: list[AssistantTurn | Exception] | None = None) -> FakeProvider:
    """Make every endpoint use a FakeProvider with these queued replies."""
    provider = FakeProvider(list(replies), turns)
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return provider


@pytest.fixture
def client() -> Iterator[TestClient]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    upload_limiter.reset()
    analysis_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_pdf(text: str) -> bytes:
    """Build a minimal, valid one-page PDF containing `text` (no external libraries)."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)
