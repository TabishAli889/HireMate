"""Agent tool registry.

Each tool has: a name + description the LLM sees, a human label for the progress UI, a precondition
check (so the LLM can't run steps out of order), and a `run` function that does the real work and
returns a short factual observation for the LLM.

Phase 5 added tailor_bullets, write_cover_letter and generate_interview_questions; Phase 6 adds
save_application. Adding a tool = adding one entry to TOOLS.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.schemas.application import STATUS_LABELS
from app.services import document_service as docs
from app.services import job_scraper
from app.services.agent.state import AgentState, ToolContext
from app.services.application_service import save_job_to_tracker
from app.services.job_service import extract_or_reuse, get_job, plan_or_reuse, score_or_reuse
from app.services.llm import ToolCall

FINISH = "finish"


@dataclass(frozen=True)
class Tool:
    name: str
    label: str
    description: str
    check: Callable[[AgentState], str | None]
    run: Callable[[ToolContext, dict[str, Any]], str]

    def spec(self) -> dict[str, Any]:
        """OpenAI/Groq function-calling schema. Tools take no arguments: inputs live in the agent state."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}},
            },
        }


FINISH_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": FINISH,
        "description": "End the run. Call this when the request is complete or cannot continue.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "1-2 sentences for the user: what was done, or what they need to do next.",
                }
            },
            "required": ["summary"],
        },
    },
}


def _list(items: list[str], limit: int = 12) -> str:
    return ", ".join(items[:limit]) + ("…" if len(items) > limit else "") if items else "none"


# ---------- scrape_job_url ----------


def _check_scrape(state: AgentState) -> str | None:
    if state.posting_text:
        return "The posting text is already available. Continue with the next step."
    if not state.url:
        return "No job URL was provided."
    return None


def _run_scrape(ctx: ToolContext, _args: dict[str, Any]) -> str:
    # Always the user's URL: the LLM can't redirect the fetch somewhere else.
    ctx.state.posting_text = job_scraper.scrape_job_url(ctx.state.url or "")
    return f"Fetched the job page: {len(ctx.state.posting_text):,} characters of posting text are now available."


# ---------- extract_job_requirements ----------


def _check_extract(state: AgentState) -> str | None:
    if state.job_id is not None:
        return "The requirements were already extracted and the job is saved."
    if not state.posting_text:
        return "No posting text yet. If a job URL was given, call scrape_job_url first."
    return None


def _run_extract(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job, reused = extract_or_reuse(ctx.db, ctx.llm, ctx.state.posting_text or "", url=ctx.state.url, max_retries=ctx.max_retries)
    ctx.state.job_id = job.id
    ctx.state.has_match = job.match_result is not None
    ctx.publish_job(job)
    prefix = f"This exact posting was analyzed before (job #{job.id}); reused its saved requirements. " if reused else ""
    return prefix + (
        f"Saved job #{job.id}: “{job.title or 'Untitled'}”{f' at {job.company}' if job.company else ''}. "
        f"Seniority: {job.seniority}. Required skills ({len(job.required_skills)}): {_list(job.required_skills)}. "
        f"Nice to have ({len(job.nice_to_have_skills)}): {_list(job.nice_to_have_skills)}."
    )


# ---------- score_match ----------


def _check_score(state: AgentState) -> str | None:
    if state.job_id is None:
        return "No saved job yet. Call extract_job_requirements first."
    if state.scored:
        return "The match was already scored in this run."
    if not state.has_profile:
        return "The user has no profile. Call finish and ask them to upload their resume in the Profile page."
    return None


def _run_score(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    result, reused = score_or_reuse(ctx.db, ctx.llm, job, max_retries=ctx.max_retries)
    ctx.state.scored = ctx.state.has_match = True
    ctx.publish_job(job)
    prefix = "The profile has not changed since this job was scored, so the saved score is kept. " if reused else ""
    return prefix + (
        f"Match score {result.score}/100. Matched: {_list([m.skill for m in result.matched_skills])}. "
        f"Missing required: {_list(result.missing_required)}. Missing nice-to-have: {_list(result.missing_nice)}."
    )


# ---------- plan_skill_gaps ----------


def _check_plan(state: AgentState) -> str | None:
    if not state.has_match:
        return "There is no match score yet. Call score_match first."
    if state.planned:
        return "The skill plan was already written in this run."
    return None


def _run_plan(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    match, reused = plan_or_reuse(ctx.db, ctx.llm, job, max_retries=ctx.max_retries)
    ctx.state.planned = True
    ctx.publish_job(job)
    if not match.missing_required and not match.missing_nice:
        return "No missing skills, so no learning plan is needed."
    plan = match.gap_plan
    noun = "skill" if len(plan) == 1 else "skills"
    verb = "Kept the existing learning plan" if reused else "Wrote a learning plan"
    return f"{verb} for {len(plan)} {noun}, in order: {_list([item.skill for item in plan])}."


# ---------- tailor_bullets / write_cover_letter / generate_interview_questions ----------


def _needs_scored_job(state: AgentState) -> str | None:
    if state.job_id is None:
        return "No saved job yet. Call extract_job_requirements first."
    if not state.has_profile:
        return "The user has no profile. Call finish and ask them to upload their resume in the Profile page."
    if not state.has_match:
        return "Score the match first (call score_match): it decides which skills may be mentioned."
    return None


def _check_tailor(state: AgentState) -> str | None:
    return "The bullets were already tailored in this run." if state.tailored else _needs_scored_job(state)


def _run_tailor(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    result, reused = docs.tailoring_or_reuse(ctx.db, ctx.llm, job, max_retries=ctx.max_retries)
    ctx.state.tailored = True
    ctx.publish_job(job)
    changed = sum(1 for b in result.bullets if b.changed)
    guarded = sum(1 for b in result.bullets if b.guard_note)
    top = result.projects[0].name if result.projects else "none"
    text = "Kept the existing tailored bullets (profile unchanged). " if reused else ""
    text += f"{changed} of {len(result.bullets)} bullets rewritten for this job; top project: {top}."
    if guarded:
        text += f" {guarded} rewrite(s) were rejected by the honesty check and the originals kept."
    return text


def _check_letter(state: AgentState) -> str | None:
    return "The cover letter was already written in this run." if state.letter_written else _needs_scored_job(state)


def _run_letter(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    tone = ctx.state.tone if ctx.state.tone in ("professional", "friendly", "confident") else "professional"
    letter, reused = docs.cover_letter_or_reuse(ctx.db, ctx.llm, job, tone=tone, max_retries=ctx.max_retries)  # type: ignore[arg-type]
    ctx.state.letter_written = True
    ctx.publish_job(job)
    words = len(letter.body.split())
    text = f"Kept the existing {tone} cover letter. " if reused else f"Wrote a {tone} cover letter ({words} words). "
    if letter.warnings:
        text += f"{len(letter.warnings)} thing(s) for the user to double-check."
    return text.strip()


def _check_interview(state: AgentState) -> str | None:
    if state.interview_prepared:
        return "Interview questions were already prepared in this run."
    if state.job_id is None:
        return "No saved job yet. Call extract_job_requirements first."
    if not state.has_profile:
        return "The user has no profile. Call finish and ask them to upload their resume in the Profile page."
    return None


def _run_interview(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    prep, reused = docs.interview_prep_or_reuse(ctx.db, ctx.llm, job, max_retries=ctx.max_retries)
    ctx.state.interview_prepared = True
    ctx.publish_job(job)
    categories = sorted({q.category for q in prep.questions})
    prefix = "Kept the existing interview questions. " if reused else ""
    return f"{prefix}{len(prep.questions)} likely questions ready ({', '.join(categories)}), each with an answer hint."


# ---------- save_application ----------


def _check_save(state: AgentState) -> str | None:
    if state.application_saved:
        return "The job was already saved to the tracker in this run."
    if state.job_id is None:
        return "No saved job yet. Call extract_job_requirements first."
    return None


def _run_save(ctx: ToolContext, _args: dict[str, Any]) -> str:
    job = get_job(ctx.db, ctx.state.job_id or 0)
    card, created = save_job_to_tracker(ctx.db, job)
    ctx.state.application_saved = True
    ctx.publish_job(job)
    if created:
        return f"Added “{card.title}” to the user's application tracker in the Saved column."
    return f"This job is already on the user's application tracker (column: {STATUS_LABELS[card.status]}). Nothing changed."


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool(
            name="scrape_job_url",
            label="Fetching the job page",
            description="Download the job posting from the URL the user gave. Only needed when there is a URL and no posting text.",
            check=_check_scrape,
            run=_run_scrape,
        ),
        Tool(
            name="extract_job_requirements",
            label="Extracting job requirements",
            description="Read the posting text and save the job's title, company, required and nice-to-have skills, seniority and responsibilities.",
            check=_check_extract,
            run=_run_extract,
        ),
        Tool(
            name="score_match",
            label="Scoring your match",
            description="Compare the saved job with the user's profile: 0-100 score, matched and missing skills, short explanation.",
            check=_check_score,
            run=_run_score,
        ),
        Tool(
            name="plan_skill_gaps",
            label="Planning your skill gaps",
            description="Write an ordered learning plan for the skills the job wants that the profile lacks. Needs a match score first.",
            check=_check_plan,
            run=_run_plan,
        ),
        Tool(
            name="tailor_bullets",
            label="Tailoring your resume bullets",
            description="Rewrite the user's existing resume bullets to fit this job (no new facts) and rank their projects. Needs a match score.",
            check=_check_tailor,
            run=_run_tailor,
        ),
        Tool(
            name="write_cover_letter",
            label="Writing your cover letter",
            description="Write a cover letter for this job in the requested tone, using only the user's real experience. Needs a match score.",
            check=_check_letter,
            run=_run_letter,
        ),
        Tool(
            name="generate_interview_questions",
            label="Preparing interview questions",
            description="Generate 8 likely interview questions for this job with answer hints from the user's real projects.",
            check=_check_interview,
            run=_run_interview,
        ),
        Tool(
            name="save_application",
            label="Saving to your tracker",
            description="Add the saved job to the user's application tracker (Saved column). Safe to call once; it never duplicates.",
            check=_check_save,
            run=_run_save,
        ),
    ]
}


def tool_specs() -> list[dict[str, Any]]:
    return [tool.spec() for tool in TOOLS.values()] + [FINISH_SPEC]


def requested_documents(request: str) -> set[str]:
    """Which follow-up tools (Phase 5-6) a request asks for (used only by the deterministic fallback)."""
    text = request.casefold()
    if "prepare" in text or "application" in text:
        return {"tailor_bullets", "write_cover_letter", "generate_interview_questions", "save_application"}
    wanted = set()
    if re.search(r"\b(save|track|tracker|board)\b", text):
        wanted.add("save_application")
    if "tailor" in text or "bullet" in text or "resume" in text:
        wanted.add("tailor_bullets")
    if "cover letter" in text or "letter" in text:
        wanted.add("write_cover_letter")
    if "interview" in text:
        wanted.add("generate_interview_questions")
    return wanted


def next_fallback_tool(state: AgentState) -> str | None:
    """Deterministic sequence used when the LLM planner can't produce valid tool calls.

    'Analyze' requests: extract → score → plan. Requests that ask for documents continue with the ones
    asked for ("Prepare my application" = tailor → cover letter → interview questions → save to tracker).
    """
    if state.job_id is None and not state.posting_text:
        return "scrape_job_url" if state.url else None
    if state.job_id is None:
        return "extract_job_requirements"
    if not state.scored and state.has_profile:
        return "score_match"
    if state.has_match and not state.planned:
        return "plan_skill_gaps"
    wanted = requested_documents(state.request)
    if not state.has_match:
        # Documents need a score; saving to the tracker doesn't.
        return "save_application" if "save_application" in wanted and not state.application_saved else None
    if "tailor_bullets" in wanted and not state.tailored:
        return "tailor_bullets"
    if "write_cover_letter" in wanted and not state.letter_written:
        return "write_cover_letter"
    if "generate_interview_questions" in wanted and not state.interview_prepared:
        return "generate_interview_questions"
    if "save_application" in wanted and not state.application_saved:
        return "save_application"
    return None


def recover_tool_call(failed_output: str, attempt: int = 1) -> ToolCall | None:
    """Rescue a malformed tool call: our tools take no arguments, so the name is all we need.

    Groq returns the model's rejected output; if it names exactly one known tool, use that tool.
    Ambiguous output (several tool names, e.g. in a plan) is not guessed at.
    """
    names = {name for name in [*TOOLS, FINISH] if re.search(rf"(?<![a-z_]){re.escape(name)}(?![a-z_])", failed_output)}
    if len(names) != 1:
        return None
    return ToolCall(id=f"recovered_{attempt}", name=names.pop(), arguments={})
