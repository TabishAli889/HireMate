"""POST /agent/run: the tool-using agent, streamed as Server-Sent Events."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import analysis_limiter
from app.schemas.agent import AgentRunRequest
from app.services.agent import AgentRunner, stream_agent_events
from app.services.agent.sse import SSE_HEADERS
from app.services.job_service import get_job
from app.services.llm import LLMProvider, get_llm_provider

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/run",
    dependencies=[Depends(analysis_limiter)],
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "run, step, notice, job, done | error events"}},
)
async def run_agent(
    body: AgentRunRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMProvider, Depends(get_llm_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Run the agent on a request like "Analyze this job" and stream each tool step as it happens.

    Validation, missing API key, unknown job and rate limits fail fast with a normal JSON error;
    once streaming starts, problems arrive as an `error` event.
    """
    if body.job_id is not None:
        get_job(db, body.job_id)  # 404 before opening the stream
    runner = AgentRunner(llm=llm, settings=settings, body=body)
    return StreamingResponse(stream_agent_events(runner, request), media_type="text/event-stream", headers=SSE_HEADERS)
