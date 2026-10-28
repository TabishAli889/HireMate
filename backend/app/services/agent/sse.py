"""Server-Sent Events bridge: runs the (synchronous) agent in a worker thread and streams its events."""

import asyncio
import json
import threading
from collections.abc import AsyncIterator
from typing import Any

from starlette.requests import Request

from app.services.agent.runner import AgentRunner

TERMINAL_EVENTS = {"done", "error"}
HEARTBEAT_SECONDS = 15.0
SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def format_sse(event: str, data: dict[str, Any]) -> str:
    """One SSE message: `event: <name>` + a single-line JSON `data:` payload."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def stream_agent_events(runner: AgentRunner, request: Request) -> AsyncIterator[str]:
    """Yield SSE messages until the run ends; stop the agent if the browser disconnects."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
    cancelled = threading.Event()

    def emit(event: str, data: dict[str, Any]) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, (event, data))
        except RuntimeError:  # event loop already closed (client went away)
            cancelled.set()

    worker = loop.run_in_executor(None, runner.run, emit, cancelled.is_set)
    try:
        while True:
            try:
                event, data = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                if await request.is_disconnected():
                    return
                yield ": keep-alive\n\n"  # comment line keeps proxies from closing an idle stream
                continue
            yield format_sse(event, data)
            if event in TERMINAL_EVENTS:
                break
        await worker
    finally:
        cancelled.set()
