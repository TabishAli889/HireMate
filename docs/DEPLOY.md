# Deploying HireMate

**Setup:** the API runs on **Render**, the web app on **Vercel**, and the data in **Neon Postgres**. All three have free plans.

```
Browser ──HTTPS + site password──▶ Vercel (Next.js)
                                     │  /api/backend/* proxy adds X-API-Key
                                     ▼
                                  Render (FastAPI) ──▶ Groq
                                     │
                                     ▼
                                  Neon (Postgres)
```

Why this setup:

- **Render's free web services lose local files** on every restart, redeploy or spin-down, so SQLite would be wiped. Neon's free Postgres keeps your data and doesn't expire. Render's own free Postgres is deleted after 30 days.
- **Only the proxy can call the API.** Render rejects requests without the shared `API_KEY`. The browser never sees that key or the Render URL.
- **The whole site sits behind a password** (`SITE_USERNAME` / `SITE_PASSWORD`), because your resume lives in it.

Free-plan behaviour to expect:

- Render sleeps after 15 minutes idle, and the first request afterwards takes about a minute.
- Neon pauses after 5 minutes idle and wakes in a moment.
- Vercel functions can run for up to 300 s. That covers a full "Prepare application" run.
- Vercel rejects request bodies over 4.5 MB, so the upload limit is set to **4 MB** on Vercel.

---

## 0. Before you start

- [ ] Push the project to GitHub. Commit `frontend/package-lock.json`, but **never** `.env`, `.env.local` or `*.db`. The `.gitignore` already handles this.
- [ ] Run `pytest -q` in `backend` and `npm run typecheck && npm run lint && npm run build` in `frontend`, and make sure all pass.
- [ ] Have your Groq API key ready.

## 1. Database: Neon

1. Sign up at <https://neon.com> and create a project in the region closest to you (for example AWS Singapore).
2. Copy the **connection string**. It looks like `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
3. That string is your `DATABASE_URL`. HireMate adds the right driver itself, and the tables are created on first start.

## 2. API: Render

1. In Render, click **New + → Blueprint** and pick your repo. Render reads `render.yaml`.
2. When asked, fill in:
   - `GROQ_API_KEY`: your key.
   - `DATABASE_URL`: the Neon string.
   - `CORS_ORIGINS`: put `https://localhost` for now; you'll set the real Vercel URL in step 4.
3. Deploy. When it's live, open `https://<your-service>.onrender.com/health`. You should see `"status":"ok"` and `"llm_configured":true`.
4. Open the service's **Environment** tab and copy the generated **`API_KEY`**. You need it for Vercel.

Checks:

- `https://<your-service>.onrender.com/profile` should return **401** "Missing or invalid API key."
- `/docs` should return **404**, because docs are hidden in production.

## 3. Web app: Vercel

1. In Vercel, click **Add New → Project**, import the repo, and set **Root Directory** to `frontend`. The framework is detected as Next.js.
2. Add these environment variables for Production:

| Name | Value |
| --- | --- |
| `BACKEND_URL` | `https://<your-service>.onrender.com` (no trailing slash) |
| `BACKEND_API_KEY` | the `API_KEY` from Render |
| `SITE_USERNAME` | any username you like |
| `SITE_PASSWORD` | a strong password (20+ characters, from a password manager) |
| `NEXT_PUBLIC_MAX_UPLOAD_MB` | `4` |

3. Deploy. `frontend/vercel.json` runs the functions in Singapore (`sin1`), next to the Render API.

## 4. Connect the two

1. Copy your Vercel URL, for example `https://hiremate-yourname.vercel.app`.
2. In Render, set `CORS_ORIGINS` to that URL and save. The service redeploys.

## 5. Smoke test the live site

- [ ] Opening the site asks for the username and password, and a wrong password is refused.
- [ ] The sidebar shows **API online**. The first load after a sleep can take about a minute.
- [ ] Upload your resume (under 4 MB) and the Profile fills in.
- [ ] Analyze a job by pasting the text. The agent's steps stream live.
- [ ] **Prepare application** finishes, and the Resume, Cover letter and Interview tabs fill in.
- [ ] Export the resume and cover letter PDFs and check they open cleanly, with no black boxes.
- [ ] Drag a card on the board, then refresh. It stays where you put it.
- [ ] Redeploy the Render service, then refresh the site. **All your data is still there** (that's Postgres doing its job).

## Running everything with Docker (optional)

```bash
cp backend/.env.example backend/.env   # add GROQ_API_KEY
docker compose up --build
```

- Open <http://localhost:3000>. API docs are at <http://localhost:8000/docs>.
- The SQLite database lives in the `hiremate-data` volume, so it survives `docker compose down`.
- `docker compose down -v` deletes it.

The Docker setup is for running on your own machine. To put it on a server, add `ENVIRONMENT=production`, a long `API_KEY` (and the same value as `BACKEND_API_KEY` for the frontend), and HTTPS in front of it.

## Production settings reference

| Where | Variable | Notes |
| --- | --- | --- |
| Render | `ENVIRONMENT=production` | The API refuses to start without a 24+ character `API_KEY`, and hides `/docs` |
| Render | `API_KEY` | Generated by the blueprint. The same value goes into Vercel's `BACKEND_API_KEY` |
| Render | `DATABASE_URL` | A Postgres URL. `postgres://` and `postgresql://` both work |
| Render | `CORS_ORIGINS` | Your Vercel URL |
| Render | `MAX_UPLOAD_MB=4` | Matches Vercel's request size limit |
| Vercel | `BACKEND_URL`, `BACKEND_API_KEY` | Read by the server-side proxy only, never sent to the browser |
| Vercel | `SITE_USERNAME`, `SITE_PASSWORD` | Turn on the site-wide login prompt |
| Vercel | `NEXT_PUBLIC_MAX_UPLOAD_MB=4` | The browser-side upload check |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Every page shows "The HireMate API is unreachable" | Render is waking up; wait a minute. Otherwise check that `BACKEND_URL` has no typo or trailing slash |
| API calls fail with "Missing or invalid API key" | Vercel's `BACKEND_API_KEY` doesn't match Render's `API_KEY`. Redeploy Vercel after changing it |
| Render deploy fails with `InsecureProductionConfig` | `API_KEY` is missing or too short |
| Resume upload fails with 413 | The PDF is over 4 MB. Export a smaller PDF (no embedded images) |
| Data disappears after a restart | `DATABASE_URL` is still SQLite. Use the Neon URL |
| Agent runs cut off after about 5 minutes | That's Vercel Hobby's function limit. Rerun it; finished steps are saved and reused |
