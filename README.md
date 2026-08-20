# FieldProxy AgentBench

Regression-testing platform for AI dispatch agents. Real execution,
deterministic grading, honest numbers — nothing is simulated.

## Stack

| Layer | Tech | Location |
|---|---|---|
| Frontend | Next.js (App Router) | `apps/web` |
| API | FastAPI + SQLAlchemy + Alembic | `apps/api` |
| Database | PostgreSQL 16 (Docker) | `docker-compose.yml` |
| Engines | policy rules · Gemini REST · LangGraph | `apps/api/app/services/` |
| Scenarios | 13 cases + world fixture | `scenarios/` |

## Local quickstart

```bash
make dev-db                          # Postgres (:5434) + Redis (:6379)
cd apps/api
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/alembic upgrade head     # apply migrations
./.venv/bin/python -m scripts.seed   # world + cases + 3 real benchmark runs
make dev-api                         # FastAPI on :8001
make dev-web                         # Next.js on :3000
```

Optional: put `GEMINI_API_KEY` in `apps/api/.env` to execute the two
LLM agent versions (v2.0-llm, v2.1-graph) for real — free keys at
https://aistudio.google.com. Without a key they record honest errors.

## Deployment

**Frontend → Vercel** (the Next.js app):

1. Import the repo in Vercel, set **Root Directory = `apps/web`**.
2. Add env var `NEXT_PUBLIC_API_URL` = your live API URL (it is baked
   into the client bundle at build time).
3. Deploy.

**Backend → Render** (free tier). The API needs a persistent server and a
real PostgreSQL database — benchmark runs execute inline and are persisted,
which Vercel's serverless model cannot do. Everything is pre-configured:

1. Push this repo to GitHub (already done).
2. On [render.com](https://render.com): **New → Blueprint** → select the repo.
   `render.yaml` creates the API service (Docker) + free Postgres, wires
   `DATABASE_URL`, and seeds real benchmark data on first boot.
3. Deploy. Your API lands at `https://agentbench-api.onrender.com`
   (check the Render dashboard for the exact URL).
4. Point the frontend at it:
   ```bash
   cd apps/web
   vercel env add NEXT_PUBLIC_API_URL production   # paste the Render URL
   vercel --prod --yes                             # redeploy to bake it in
   ```

Notes: the free Render instance sleeps after ~15 min idle — the first request
after a pause takes ~30 s while it boots. To run the two LLM agent versions,
add `GEMINI_API_KEY` in the Render dashboard (free keys: aistudio.google.com).
`CORS_ORIGINS` in `render.yaml` must include your Vercel domain.

## Commands

`make install · dev-db · dev-web · dev-api · migrate · test · lint`
