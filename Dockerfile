# AgentBench API — container image for Render/Railway/Fly/VPS.
# Build context: repository root (docker build -f Dockerfile .)
FROM python:3.13-slim

WORKDIR /app

# Scenario JSONs live at the repo root; bundle them so the seed script
# works on any host. AGENTBENCH_REPO_ROOT points seed.py at /app.
COPY scenarios ./scenarios

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api .

ENV PYTHONUNBUFFERED=1 \
    AGENTBENCH_REPO_ROOT=/app

EXPOSE 8001

CMD ["sh", "scripts/start.sh"]
