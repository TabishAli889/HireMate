# HireMate

An AI job application agent for students and fresh graduates. Upload your resume once, then for each job: get an honest match score with evidence, a prioritized skill plan, tailored resume bullets, a cover letter and interview prep — tracked from Saved to Offer.

> Built phase by phase. **All 8 phases complete.** Deploy guide: [`docs/DEPLOY.md`](docs/DEPLOY.md).

| Phase | Status | What it adds |
| --- | --- | --- |
| 1 | ✅ | Scaffold, theme, layout shell, dark mode, API proxy, `/health` |
| 2 | ✅ | Profile Vault: PDF upload → AI extraction → editable profile |
| 3 | ✅ | Job analyzer (text or URL) and evidence-based match scoring |
| 4 | ✅ | Agent loop with tool calling, streamed step by step (SSE) |
| 5 | ✅ | Tailored bullets (diff, accept/reject/edit, PDF), cover letters (3 tones, PDF), interview prep |
| 6 | ✅ | Application tracker: Kanban board, drag & drop, notes, deadlines, links, timeline |
| 7 | ✅ | Dashboard: stats, pipeline, deadlines, match history, skills to learn, activity |
| 8 | ✅ | Docker, Render + Vercel + Neon deployment, API key + site password, CI |

## Monorepo

```
hiremate/
├── frontend/   Next.js 14 (App Router) · TypeScript · Tailwind · shadcn-style UI · Framer Motion
└── backend/    FastAPI · Pydantic v2 · SQLAlchemy (SQLite locally, Postgres in production) · Groq (openai/gpt-oss-120b by default)
```

## Run locally

Requirements: Node 18.17+ and Python 3.11+.

### 1. Backend (terminal 1)

```bash
cd backend
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env          # Windows: copy .env.example .env  — then add GROQ_API_KEY
pytest -q
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>. The SQLite database (`hiremate.db`) and its tables are created on startup.

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
cp .env.example .env.local    # Windows: copy .env.example .env.local
npm run dev
```

Open <http://localhost:3000>.

### Or: everything in Docker

```bash
cp backend/.env.example backend/.env   # add GROQ_API_KEY
docker compose up --build              # http://localhost:3000
```

## Deploy

Render (API) + Vercel (web) + Neon (Postgres), all on free plans. The step-by-step guide, production settings and troubleshooting are in **[`docs/DEPLOY.md`](docs/DEPLOY.md)**.

Production safety built in:
- The API refuses to start in production without a long `API_KEY`. Only the Next.js proxy knows the key; anyone else gets 401.
- An optional site-wide password (`SITE_USERNAME` / `SITE_PASSWORD`) protects your resume and Groq quota.
- `/docs` is hidden in production, and security headers are set on every page.
- `postgres://` URLs work as-is. CI (GitHub Actions) runs the backend tests plus the frontend typecheck, lint and build on every push.

## How the agent works

`POST /agent/run` takes a request ("Analyze this job", "Only extract the requirements", "Re-score this job") plus one input (posting text, a URL, or a saved job) and streams Server-Sent Events: `run`, `step`, `notice`, `job`, then `done` or `error`.

1. **The LLM plans.** Each turn it sees the request, what's available and every previous tool result, and calls exactly one tool (Groq function calling) or `finish`.
2. **Tools do the work in code:** `scrape_job_url`, `extract_job_requirements`, `score_match`, `plan_skill_gaps`, `tailor_bullets`, `write_cover_letter`, `generate_interview_questions`, `save_application`. Ask "Prepare my application" and the agent runs the whole chain and puts the job on your board.
3. **Malformed tool calls:** if Groq rejects a tool call (`tool_use_failed`), the tool name is recovered from the rejected output (tools take no arguments), otherwise the planner retries before falling back.
4. **Guardrails:** tools take no free-form arguments (inputs live in a shared state, so the LLM can't change the URL or inject text); preconditions reject out-of-order or repeated calls and explain why; a step cap; if tool calling fails, a deterministic fallback finishes the standard sequence.
5. **Failure handling:** an unreadable URL → the agent asks you to paste the text; invalid LLM JSON → retried up to 2× with the validation error, then a clear message; Groq rate limit → exponential backoff with a live "waiting" notice.

## Honesty by design

- Resume extraction and job extraction are told to copy only what is written; missing fields stay empty.
- The **match score is computed in code** (70% required skills, 20% nice-to-haves, 10% seniority fit). Each matched skill shows where your profile proves it.
- "Related experience" matches must quote your profile verbatim, and the quote is verified in code.
- Every LLM output is validated against a Pydantic model. No free-text parsing.
- **Tailoring rewrites only your existing bullets.** A code check rejects any rewrite that adds a number not in the original or mentions a skill you're missing, and keeps your original instead (shown as "Honesty check kept…"). Missing metrics become `[add real number]`.
- **Cover letters** only mention your real projects and experience; anything that names a missing skill or new number is flagged under "Double-check before sending".
- Nothing is applied automatically: you accept, reject or edit each bullet, and the PDF uses only what you accepted.

## Documents API (Phase 5)

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/jobs/{id}/tailor` | Tailor bullets (`{"regenerate": true}` for fresh ones) |
| PATCH | `/jobs/{id}/tailor` | Save `decisions` (accepted/rejected/pending) and `edits` |
| GET | `/jobs/{id}/tailor/pdf` | Resume PDF with accepted rewrites |
| POST | `/jobs/{id}/cover-letter` | `{"tone": "professional\|friendly\|confident", "regenerate": false}` |
| PUT | `/jobs/{id}/cover-letter/{tone}` | Save your edited text |
| GET | `/jobs/{id}/cover-letter/{tone}/pdf` | Cover letter PDF |
| POST | `/jobs/{id}/interview-prep` | 8 questions with hints (`regenerate` optional) |

Documents are cached per job and reused until your profile changes; edited cover letters are never overwritten unless you regenerate.

## Application tracker (Phase 6)

Five columns: **Saved → Applied → Interview → Offer → Rejected**.

- **Add cards** with "Save to tracker" on an analyzed job, by running "Prepare application" (the agent's `save_application` tool), or by hand for any role.
- **Move cards** by dragging them, with **Alt + ←/→** (column) and **Alt + ↑/↓** (order) on the keyboard, or by picking a status in the card's dialog (works on phones).
- **Each card** keeps notes, a deadline (overdue / due soon highlights), the posting link, and a **timeline** of everything that happened ("Moved from Applied to Interview").
- One card per analyzed job; deleting a card never deletes the analysis or its documents.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/applications` | Every card, in column order and position |
| POST | `/applications` | Add a card (`job_id`, or `title`/`company`/`link`), optional `status`, `deadline`, `notes` |
| GET | `/applications/{id}` | One card with its timeline |
| PATCH | `/applications/{id}` | Edit `title`, `company`, `link`, `notes`, `deadline` (`null` clears it) |
| POST | `/applications/{id}/move` | `{"status": "interview", "position": 0}` |
| DELETE | `/applications/{id}` | Remove the card |

## Dashboard (Phase 7)

`GET /dashboard` returns everything the home page shows in one request. It's computed from your board, analyzed jobs and profile, with no AI calls:

- **Applications**, **interview rate** (cards that reached Interview or Offer ÷ cards past Saved), **average match** and **offers**.
- **Pipeline** per column, **upcoming deadlines** (next 14 days plus overdue, open cards only), **match score history** (last 12 scored jobs).
- **Skills to learn next:** required skills your profile doesn't show, counted once per scored job. It's a quick way to see which gap would unlock the most jobs.
- **Recent activity:** timeline events and analyses, newest first.

A brand-new account (no jobs, no applications) sees the three-step getting-started guide instead.

## Screenshots

Add yours to `docs/screenshots/` (light and dark), then uncomment the lines below:

<!--
![Dashboard](docs/screenshots/dashboard.png)
![Analyze a job](docs/screenshots/analyze.png)
![Tailored resume](docs/screenshots/tailored-resume.png)
![Application board](docs/screenshots/applications.png)
![Dark mode](docs/screenshots/dashboard-dark.png)
-->

## Architecture notes

- **Theme:** all colors, radius, shadows, spacing and layout sizes live in `frontend/app/theme.css`.
- **API proxy:** the browser only calls `/api/backend/*`; a Next.js route forwards to `BACKEND_URL` server-side and streams responses (SSE included).
- **Security:** URL fetching blocks private/internal addresses and re-checks redirects; PDFs are validated (type, magic bytes, 5 MB); per-client rate limits on uploads and AI calls; secrets only in env vars.

## Configuration (`backend/.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | — | Required for AI features |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Main model (extraction, scoring, writing) |
| `GROQ_PLANNER_MODEL` | empty (= main model) | Optional cheaper model for the agent planner, e.g. `openai/gpt-oss-20b` |
| `GROQ_REASONING_EFFORT` | `low` | gpt-oss thinking effort: `low` / `medium` / `high` |
| `GROQ_PLANNER_REASONING_EFFORT` | `medium` | Thinking effort for the agent planner (more reliable tool calls) |
| `LLM_MAX_RETRIES` | `2` | Re-asks when LLM JSON fails validation |
| `AGENT_MAX_STEPS` | `12` | Tool-call cap per agent run |
| `DATABASE_URL` | `sqlite:///./hiremate.db` | SQLAlchemy URL |
| `SEED_DEMO_DATA` | `false` | Demo profile for screenshots; `python seed.py --reset` / `--clear` |
| `MAX_UPLOAD_MB` | `5` | Resume size limit |
| `UPLOAD_RATE_LIMIT_PER_MINUTE` | `5` | Resume uploads per client |
| `ANALYSIS_RATE_LIMIT_PER_MINUTE` | `10` | AI analysis / agent runs per client |

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl/⌘ + K` | Command palette |
| `Ctrl/⌘ + B` | Collapse / expand sidebar |
| `Ctrl/⌘ + Enter` | Run the agent from the job text box |

## Final checklist

- [x] Every LLM output validated with Pydantic, with up to 2 retries that show the model the validation error
- [x] Honesty rules enforced in code: no invented skills or numbers in bullets or letters; missing metrics become `[add real number]`
- [x] Agent with real tool calling, live SSE progress, step cap, and deterministic fallback
- [x] Failure handling: an unreadable URL asks you to paste the text; rate limits back off with a live notice
- [x] PDF-only uploads (type + magic bytes + size), SSRF-safe URL fetching, per-client rate limits
- [x] No secrets in code; `.env` files are git-ignored; API key + site password in production
- [x] Dark/light themes from one token file, keyboard shortcuts, screen-reader labels, empty states, skeletons
- [x] Tests for schemas, scoring, retries, the agent, documents, the tracker, the dashboard and production security
- [ ] Your screenshots in `docs/screenshots/` (see the guide there)

