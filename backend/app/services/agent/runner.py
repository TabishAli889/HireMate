"""The agent loop.

Each turn the LLM sees the request, what's available and every previous tool result, and calls ONE
tool (or `finish`). Guardrails:
- tools take no free-form arguments; inputs come from AgentState, so the LLM can't inject data or URLs
- a precondition check rejects out-of-order or repeated calls, and tells the LLM why
- a step cap (AGENT_MAX_STEPS)
- if the LLM can't produce valid tool calls, a deterministic fallback finishes the standard sequence
Progress is reported through `emit(event, data)`, which the SSE layer streams to the browser.
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.models.job import Job
from app.schemas.agent import AgentRunRequest
from app.services.agent.state import AgentState, ToolContext
from app.services.agent.tools import FINISH, TOOLS, next_fallback_tool, recover_tool_call, tool_specs
from app.services.job_service import get_job, get_match, job_to_out
from app.services.llm import AssistantTurn, ChatMessage, LLMProvider
from app.services.llm.errors import LLMNotConfiguredError, LLMRateLimitError, LLMToolCallError, LLMUnavailableError
from app.services.llm.provider import rate_limit_listener
from app.services.profile_service import get_profile

logger = logging.getLogger("hiremate.agent")

Emit = Callable[[str, dict[str, Any]], None]

# Errors that end the whole run (retrying another tool won't help).
FATAL_ERRORS = (LLMRateLimitError, LLMUnavailableError, LLMNotConfiguredError)
MAX_INVALID_CALLS = 2
PLANNER_ATTEMPTS = 3  # retry malformed tool calls before falling back

SYSTEM_PROMPT = """
You are HireMate's job-application agent. You help a student or fresh graduate by calling tools.

How to work:
- Call exactly ONE tool per turn. Tools need no arguments: their inputs are already stored for you.
- If there is a job URL but no posting text, call scrape_job_url first. If scraping fails,
  call finish and ask the user to paste the job text instead.
- extract_job_requirements needs posting text. score_match needs a saved job and a profile.
  plan_skill_gaps needs a match score.
- "Analyze this job" means: extract the requirements, score the match, then plan skill gaps.
- "Prepare my application" means: everything in "Analyze", then tailor_bullets, write_cover_letter,
  generate_interview_questions and finally save_application. tailor_bullets and write_cover_letter
  need a match score first.
- save_application puts the saved job on the user's application tracker. Call it when the request
  asks to save or track the job, or as the last step of "Prepare my application".
- Do only what the request asks for. Never repeat a tool that already succeeded.
- Tool results are facts from the system. Never invent results or skills.
- When the request is done, or cannot continue, call finish with 1-2 plain sentences for the user.
""".strip()


def _context_message(state: AgentState, job: Job | None) -> str:
    lines = [f"Request: {state.request}", "", "What is available:"]
    lines.append(f"- Job URL: {state.url} (not fetched yet)" if state.url else "- Job URL: none")
    if state.posting_text and job is None:
        lines.append(f"- Job posting text: provided ({len(state.posting_text):,} characters)")
    if job is not None:
        scored = "already scored earlier" if state.has_match else "not scored yet"
        lines.append(f"- Saved job #{job.id}: “{job.title or 'Untitled'}” (requirements already extracted; {scored})")
    lines.append(f"- Cover letter tone requested: {state.tone}")
    lines.append(
        "- Candidate profile: present"
        if state.has_profile
        else "- Candidate profile: MISSING (scoring is impossible; tell the user to upload their resume)"
    )
    return "\n".join(lines)


def _default_summary(state: AgentState, db: Session) -> str:
    if state.job_id is None:
        return "Finished without saving a job."
    match = get_match(get_job(db, state.job_id))
    if match is not None and state.scored:
        return f"Your match score is {match.score}/100. See the details and your skill plan below."
    return "The job requirements are saved."


class AgentRunner:
    """Runs one agent request synchronously (in a worker thread) and reports progress via `emit`."""

    def __init__(self, *, llm: LLMProvider, settings: Settings, body: AgentRunRequest):
        self.llm = llm
        self.max_steps = settings.agent_max_steps
        self.max_retries = settings.llm_max_retries
        self.body = body

    def run(self, emit: Emit, is_cancelled: Callable[[], bool]) -> None:
        """Always ends by emitting exactly one terminal event: `done` or `error`."""
        token = rate_limit_listener.set(
            lambda delay: emit(
                "notice",
                {"kind": "rate_limit", "message": f"Groq rate limit reached. Waiting {delay:.0f}s, then retrying…"},
            )
        )
        try:
            with SessionLocal() as db:
                self._run(db, emit, is_cancelled)
        except AppError as exc:
            emit("error", {"message": exc.detail})
        except Exception:
            logger.exception("Agent run crashed")
            emit("error", {"message": "Something went wrong while the agent was working. Please try again."})
        finally:
            rate_limit_listener.reset(token)

    def _initial_state(self, db: Session) -> tuple[AgentState, Job | None]:
        body = self.body
        state = AgentState(
            request=body.request,
            url=str(body.url) if body.url else None,
            posting_text=body.text.strip() if body.text else None,
            has_profile=get_profile(db) is not None,
            tone=body.tone,
        )
        job = None
        if body.job_id is not None:
            job = get_job(db, body.job_id)
            state.job_id = job.id
            state.posting_text = job.raw_text
            state.has_match = job.match_result is not None
        return state, job

    def _run(self, db: Session, emit: Emit, is_cancelled: Callable[[], bool]) -> None:
        state, job = self._initial_state(db)

        def publish_job(updated: Job) -> None:
            emit("job", job_to_out(updated).model_dump(mode="json"))

        ctx = ToolContext(db=db, llm=self.llm, state=state, max_retries=self.max_retries, publish_job=publish_job)
        emit("run", {"request": state.request})
        if job is not None:
            publish_job(job)

        messages: list[ChatMessage] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _context_message(state, job)},
        ]
        specs = tool_specs()
        fallback = False
        invalid_calls = 0
        summary: str | None = None

        for step in range(1, self.max_steps + 1):
            if is_cancelled():
                logger.info("Agent run cancelled by the client")
                return

            call_id: str | None = None
            if fallback:
                name = next_fallback_tool(state)
                if name is None:
                    break
            else:
                turn = self._plan(messages, specs)
                if turn is None:
                    fallback = True
                    emit("notice", {"kind": "fallback", "message": "The planner had trouble choosing a tool, so the standard sequence is being used."})
                    continue
                call = turn.tool_calls[0] if turn.tool_calls else None
                if call is None:
                    summary = turn.content.strip() or None
                    break
                messages.append(AssistantTurn(content=turn.content, tool_calls=[call]).as_message())
                call_id, name = call.id, call.name
                if name == FINISH:
                    summary = str(call.arguments.get("summary", "")).strip() or None
                    break

            observation, ok = self._execute(ctx, name, step, emit)
            if call_id is not None:
                messages.append({"role": "tool", "tool_call_id": call_id, "content": observation})

            if ok is None:  # invalid call: unknown tool or failed precondition (no step shown to the user)
                invalid_calls += 1
                if invalid_calls >= MAX_INVALID_CALLS and not fallback:
                    fallback = True
                    emit("notice", {"kind": "fallback", "message": "The planner chose steps out of order, so the standard sequence is being used."})
                if fallback and call_id is None:
                    break
            elif not ok and fallback:
                break  # a real tool failed and nobody is planning around it
        else:
            emit("notice", {"kind": "info", "message": f"Stopped after {self.max_steps} steps (safety limit)."})

        emit("done", {"summary": summary or _default_summary(state, db), "job_id": state.job_id})

    def _plan(self, messages: list[ChatMessage], specs: list[dict[str, Any]]) -> AssistantTurn | None:
        """Ask the LLM for its next tool call; None if it can't produce a valid one (→ fallback)."""
        for attempt in range(1, PLANNER_ATTEMPTS + 1):
            try:
                return self.llm.complete_with_tools(messages, specs)
            except NotImplementedError:
                return None
            except LLMToolCallError as exc:
                recovered = recover_tool_call(exc.failed_generation, attempt)
                if recovered is not None:
                    logger.info("Recovered planner tool call %r from rejected output", recovered.name)
                    return AssistantTurn(content="", tool_calls=[recovered])
                logger.info("Planner produced a malformed tool call (attempt %d/%d)", attempt, PLANNER_ATTEMPTS)
        return None

    def _execute(self, ctx: ToolContext, name: str, step: int, emit: Emit) -> tuple[str, bool | None]:
        """Run one tool. Returns (observation for the LLM, True=ok / False=tool failed / None=invalid call)."""
        tool = TOOLS.get(name)
        if tool is None:
            return f"ERROR: unknown tool “{name}”. Use one of: {', '.join(TOOLS)}, or finish.", None
        problem = tool.check(ctx.state)
        if problem:
            return f"ERROR: {problem}", None

        step_id = f"{step}-{tool.name}"
        emit("step", {"id": step_id, "tool": tool.name, "label": tool.label, "status": "running", "detail": ""})
        try:
            observation = tool.run(ctx, {})
        except FATAL_ERRORS as exc:
            emit("step", {"id": step_id, "tool": tool.name, "label": tool.label, "status": "error", "detail": exc.detail})
            raise
        except AppError as exc:
            emit("step", {"id": step_id, "tool": tool.name, "label": tool.label, "status": "error", "detail": exc.detail})
            return f"ERROR: {exc.detail}", False
        ctx.state.completed.append(tool.name)
        emit("step", {"id": step_id, "tool": tool.name, "label": tool.label, "status": "done", "detail": observation})
        return observation, True
