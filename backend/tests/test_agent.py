"""The agent loop: LLM-chosen tools, guardrails, fallback, errors and the SSE endpoint."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.schemas.agent import AgentRunRequest
from app.services import job_scraper
from app.services.agent import AgentRunner
from app.services.agent.tools import recover_tool_call
from app.services.llm.errors import LLMRateLimitError, LLMToolCallError
from tests.conftest import FakeProvider, call, use_fake_llm

POSTING = (
    "Nimbus Analytics is hiring a Backend Intern in Lahore. You will build REST APIs in Python, "
    "write SQL queries and ship services with Docker. AWS experience is a plus."
)
EXTRACTED = json.dumps(
    {
        "title": "Backend Intern",
        "company": "Nimbus Analytics",
        "seniority": "internship",
        "required_skills": ["Python", "SQL", "REST APIs", "Docker"],
        "nice_to_have_skills": ["AWS"],
    }
)
PROFILE = {"full_name": "Sara", "skills": ["Python", "PostgreSQL"], "projects": [{"name": "Bot", "bullets": ["Built REST APIs with FastAPI"]}]}
SEMANTIC = json.dumps({"matches": [{"skill": "SQL", "evidence_quote": "PostgreSQL"}]})
EXPLANATION = json.dumps({"explanation": "Solid fit: you show Python, REST APIs and SQL. Docker is the main gap."})
PLAN = json.dumps({"gap_plan": [{"skill": "Docker", "why": "They ship with it.", "first_steps": ["Dockerise Bot"]}]})

Events = list[tuple[str, dict[str, Any]]]


def run_agent(provider: FakeProvider, **body: Any) -> Events:
    events: Events = []
    runner = AgentRunner(llm=provider, settings=get_settings(), body=AgentRunRequest(**body))
    runner.run(lambda event, data: events.append((event, data)), lambda: False)
    return events


def steps(events: Events) -> list[tuple[str, str]]:
    return [(data["tool"], data["status"]) for event, data in events if event == "step"]


def last(events: Events, name: str) -> dict[str, Any]:
    return [data for event, data in events if event == name][-1]


def test_llm_plans_full_analysis(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider(
        [EXTRACTED, SEMANTIC, EXPLANATION, PLAN],
        turns=[call("extract_job_requirements"), call("score_match"), call("plan_skill_gaps"), call("finish", summary="All done.")],
    )
    events = run_agent(provider, text=POSTING)

    assert events[0] == ("run", {"request": "Analyze this job"})
    assert steps(events) == [
        ("extract_job_requirements", "running"),
        ("extract_job_requirements", "done"),
        ("score_match", "running"),
        ("score_match", "done"),
        ("plan_skill_gaps", "running"),
        ("plan_skill_gaps", "done"),
    ]
    done = last(events, "done")
    assert done["summary"] == "All done."
    final_job = last(events, "job")
    assert final_job["id"] == done["job_id"]
    assert final_job["match"]["missing_required"] == ["Docker"]
    assert final_job["match"]["gap_plan"][0]["skill"] == "Docker"
    # The LLM saw each tool's factual observation before choosing the next step.
    tool_results = [m for m in provider.tool_calls[-1] if m["role"] == "tool"]
    assert "Match score" in tool_results[1]["content"]


def test_request_controls_which_tools_run(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider([EXTRACTED], turns=[call("extract_job_requirements"), call("finish", summary="Requirements saved.")])
    events = run_agent(provider, request="Only extract the requirements, don't score", text=POSTING)
    assert [tool for tool, status in steps(events) if status == "done"] == ["extract_job_requirements"]
    assert last(events, "job")["match"] is None


def test_out_of_order_calls_are_rejected_not_run(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider(
        [EXTRACTED],
        turns=[call("score_match"), call("extract_job_requirements"), call("finish", summary="ok")],
    )
    events = run_agent(provider, text=POSTING)
    assert ("score_match", "running") not in steps(events)
    rejection = [m for m in provider.tool_calls[1] if m["role"] == "tool"][0]
    assert rejection["content"].startswith("ERROR: No saved job yet")


def test_scrape_failure_is_reported_and_agent_finishes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(url: str) -> str:
        raise job_scraper.ScrapeError()

    monkeypatch.setattr(job_scraper, "scrape_job_url", blocked)
    provider = FakeProvider([], turns=[call("scrape_job_url"), call("finish", summary="Please paste the job text.")])
    events = run_agent(provider, url="https://www.linkedin.com/jobs/view/1")
    assert steps(events) == [("scrape_job_url", "running"), ("scrape_job_url", "error")]
    assert "paste" in [d for e, d in events if e == "step"][-1]["detail"]
    assert last(events, "done")["summary"] == "Please paste the job text."


def test_url_flow_scrapes_then_extracts(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job_scraper, "scrape_job_url", lambda url: POSTING)
    provider = FakeProvider(
        [EXTRACTED], turns=[call("scrape_job_url"), call("extract_job_requirements"), call("finish", summary="Saved.")]
    )
    events = run_agent(provider, url="https://careers.example.com/backend-intern")
    assert [t for t, s in steps(events) if s == "done"] == ["scrape_job_url", "extract_job_requirements"]
    assert last(events, "job")["source_url"] == "https://careers.example.com/backend-intern"


def test_malformed_tool_call_is_retried_once(client: TestClient) -> None:
    provider = FakeProvider([EXTRACTED], turns=[LLMToolCallError(), call("extract_job_requirements"), call("finish", summary="ok")])
    events = run_agent(provider, request="Only extract", text=POSTING)
    assert not any(e == "notice" for e, _ in events)
    assert [t for t, s in steps(events) if s == "done"] == ["extract_job_requirements"]


def test_malformed_call_is_recovered_from_failed_output(client: TestClient) -> None:
    garbled = LLMToolCallError(failed_generation='<|channel|>commentary to=functions.extract_job_requirements <|message|>{}')
    provider = FakeProvider([EXTRACTED], turns=[garbled, call("finish", summary="ok")])
    events = run_agent(provider, request="Only extract", text=POSTING)
    assert not any(e == "notice" for e, _ in events)
    assert [t for t, s in steps(events) if s == "done"] == ["extract_job_requirements"]
    assert len(provider.tool_calls) == 2  # recovered without a retry call


def test_recover_tool_call_rules() -> None:
    assert recover_tool_call("to=functions.score_match {}").name == "score_match"  # type: ignore[union-attr]
    assert recover_tool_call("finish") is not None
    assert recover_tool_call("first extract_job_requirements then score_match") is None  # ambiguous
    assert recover_tool_call("rescore_matches") is None  # no whole-name match
    assert recover_tool_call("") is None


def test_fallback_when_tool_calling_keeps_failing(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider([EXTRACTED, SEMANTIC, EXPLANATION, PLAN], turns=[LLMToolCallError()] * 3)
    events = run_agent(provider, text=POSTING)
    assert any(e == "notice" and d["kind"] == "fallback" for e, d in events)
    assert [t for t, s in steps(events) if s == "done"] == ["extract_job_requirements", "score_match", "plan_skill_gaps"]
    assert "match score" in last(events, "done")["summary"].lower()


def test_missing_profile_stops_before_scoring(client: TestClient) -> None:
    provider = FakeProvider([EXTRACTED], turns=[call("extract_job_requirements"), call("score_match"), call("finish", summary="Upload your resume.")])
    events = run_agent(provider, text=POSTING)
    assert ("score_match", "running") not in steps(events)
    assert last(events, "done")["summary"] == "Upload your resume."


def test_rescore_existing_job(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    use_fake_llm(EXTRACTED)
    job_id = client.post("/jobs/analyze", json={"text": POSTING}).json()["id"]

    provider = FakeProvider([SEMANTIC, EXPLANATION, PLAN], turns=[call("score_match"), call("plan_skill_gaps"), call("finish", summary="Re-scored.")])
    events = run_agent(provider, request="Re-score this job", job_id=job_id)
    assert events[1][0] == "job"  # the saved job is published immediately
    assert [t for t, s in steps(events) if s == "done"] == ["score_match", "plan_skill_gaps"]
    assert "Saved job #" in provider.tool_calls[0][1]["content"]


def test_rate_limit_ends_run_with_error(client: TestClient) -> None:
    provider = FakeProvider([LLMRateLimitError()], turns=[call("extract_job_requirements")])
    events = run_agent(provider, text=POSTING)
    assert steps(events) == [("extract_job_requirements", "running"), ("extract_job_requirements", "error")]
    assert events[-1][0] == "error"
    assert "rate limit" in events[-1][1]["message"]


def test_repeated_invalid_calls_switch_to_fallback(client: TestClient) -> None:
    provider = FakeProvider([EXTRACTED], turns=[call("score_match")] * 2)
    events = run_agent(provider, text=POSTING)
    # Two out-of-order calls -> fallback takes over: it extracts, then stops (no profile to score against).
    assert any(e == "notice" and "out of order" in d["message"] for e, d in events)
    assert [t for t, s in steps(events) if s == "done"] == ["extract_job_requirements"]
    assert events[-1][0] == "done"
    assert len(provider.tool_calls) == 2


# ---------- HTTP / SSE ----------


def parse_sse(body: str) -> Events:
    events: Events = []
    for block in body.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        name = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = next((line[6:] for line in lines if line.startswith("data: ")), None)
        if name and data:
            events.append((name, json.loads(data)))
    return events


def test_sse_endpoint_streams_events(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    use_fake_llm(EXTRACTED, turns=[call("extract_job_requirements"), call("finish", summary="Saved.")])
    with client.stream("POST", "/agent/run", json={"request": "Just extract", "text": POSTING}) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(res.read().decode())
    assert [e for e, _ in events][0] == "run"
    assert events[-1] == ("done", {"summary": "Saved.", "job_id": events[-1][1]["job_id"]})


@pytest.mark.parametrize(
    "body",
    [{"text": POSTING, "url": "https://example.com/j"}, {}, {"text": "too short"}],
)
def test_sse_endpoint_validates_before_streaming(client: TestClient, body: dict) -> None:
    use_fake_llm()
    res = client.post("/agent/run", json=body)
    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/json")


def test_sse_endpoint_unknown_job_and_missing_key(client: TestClient) -> None:
    use_fake_llm()
    assert client.post("/agent/run", json={"job_id": 999}).status_code == 404
    client.app.dependency_overrides.clear()  # type: ignore[attr-defined]
    res = client.post("/agent/run", json={"text": POSTING})
    assert res.status_code == 503
    assert "GROQ_API_KEY" in res.json()["detail"]


def test_repeat_analysis_reuses_everything(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    turns = [call("extract_job_requirements"), call("score_match"), call("plan_skill_gaps"), call("finish", summary="ok")]
    first = run_agent(FakeProvider([EXTRACTED, SEMANTIC, EXPLANATION, PLAN], turns=list(turns)), text=POSTING)
    second_provider = FakeProvider([], turns=list(turns))  # no JSON replies queued: any AI call would fail
    second = run_agent(second_provider, text=POSTING)

    assert last(second, "done")["job_id"] == last(first, "done")["job_id"]
    assert last(second, "job")["match"]["score"] == last(first, "job")["match"]["score"]
    details = [d["detail"] for e, d in second if e == "step" and d["status"] == "done"]
    assert "analyzed before" in details[0]
    assert "saved score is kept" in details[1]
    assert details[2].startswith("Kept the existing learning plan")


TAILOR = json.dumps(
    {
        "bullets": [{"id": "proj0-b0", "rewritten": "Designed REST APIs in Python with FastAPI", "reason": "REST APIs"}],
        "project_ranking": [{"name": "Bot"}],
    }
)
LETTER = json.dumps({"paragraphs": ["I'm applying for the Backend Intern role.", "In Bot I built REST APIs with FastAPI.", "Thank you."]})
QUESTIONS = json.dumps(
    {"questions": [{"question": f"Q{i}?", "category": "project", "hint": "Use Bot.", "project": "Bot"} for i in range(8)]}
)
PREPARE = "Prepare my application: analyze, tailor my bullets, write a cover letter and interview questions."
PREP_REPLIES = [EXTRACTED, SEMANTIC, EXPLANATION, PLAN, TAILOR, LETTER, QUESTIONS]
PREP_TOOLS = [
    "extract_job_requirements",
    "score_match",
    "plan_skill_gaps",
    "tailor_bullets",
    "write_cover_letter",
    "generate_interview_questions",
    "save_application",
]


def test_prepare_my_application_runs_every_tool(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider(list(PREP_REPLIES), turns=[*(call(t) for t in PREP_TOOLS), call("finish", summary="Ready.")])
    events = run_agent(provider, request=PREPARE, text=POSTING, tone="confident")
    assert [t for t, s in steps(events) if s == "done"] == PREP_TOOLS
    job = last(events, "job")
    assert job["tailoring"]["bullets"][0]["tailored"].startswith("Designed REST APIs")
    assert set(job["cover_letters"]) == {"confident"}
    assert len(job["interview_prep"]["questions"]) == 8
    assert job["application"]["status"] == "saved"


def test_prepare_fallback_continues_past_analysis(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider(list(PREP_REPLIES), turns=[LLMToolCallError()] * 3)
    events = run_agent(provider, request=PREPARE, text=POSTING)
    assert [t for t, s in steps(events) if s == "done"] == PREP_TOOLS


def test_tailoring_needs_a_score_first(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    provider = FakeProvider([EXTRACTED], turns=[call("extract_job_requirements"), call("tailor_bullets"), call("finish", summary="ok")])
    events = run_agent(provider, request="Tailor my bullets", text=POSTING)
    assert ("tailor_bullets", "running") not in steps(events)
    rejection = [m for m in provider.tool_calls[2] if m["role"] == "tool"][-1]
    assert "Score the match first" in rejection["content"]


def test_requested_documents_from_request() -> None:
    from app.services.agent.tools import requested_documents

    assert requested_documents(PREPARE) == {"tailor_bullets", "write_cover_letter", "generate_interview_questions", "save_application"}
    assert requested_documents("Save this job to my tracker") == {"save_application"}
    assert requested_documents("Re-score my match for this saved job and refresh my skill plan.") == set()
    assert requested_documents("Tailor my resume bullets for this job") == {"tailor_bullets"}
    assert requested_documents("Write a cover letter") == {"write_cover_letter"}
    assert requested_documents("Analyze this job: extract the requirements, score my match and plan my skill gaps.") == set()


def test_save_application_is_idempotent(client: TestClient) -> None:
    client.put("/profile", json=PROFILE)
    extract = FakeProvider([EXTRACTED], turns=[call("extract_job_requirements"), call("finish", summary="ok")])
    job_id = last(run_agent(extract, request="Only extract", text=POSTING), "done")["job_id"]

    turns = [call("save_application"), call("finish", summary="Saved.")]
    first = run_agent(FakeProvider([], turns=list(turns)), request="Save this job to my tracker", job_id=job_id)
    assert "Saved column" in [d["detail"] for e, d in first if e == "step" and d["status"] == "done"][0]
    assert last(first, "job")["application"]["status"] == "saved"

    second = run_agent(FakeProvider([], turns=list(turns)), request="Save this job to my tracker", job_id=job_id)
    assert "already on the user's application tracker" in [d["detail"] for e, d in second if e == "step" and d["status"] == "done"][0]
    assert len(client.get("/applications").json()) == 1


def test_save_fallback_works_without_a_profile(client: TestClient) -> None:
    provider = FakeProvider([EXTRACTED], turns=[LLMToolCallError()] * 3)
    events = run_agent(provider, request="Save this job to my tracker", text=POSTING)
    assert [t for t, s in steps(events) if s == "done"] == ["extract_job_requirements", "save_application"]
