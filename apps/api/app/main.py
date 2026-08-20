"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings
from app.database import SessionLocal
from app.models import BenchmarkRun

settings = get_settings()


def _reap_interrupted_runs() -> None:
    """Runs stuck in queued/running after a restart can never finish — mark
    them failed so they don't block new benchmarks forever."""
    db = SessionLocal()
    try:
        stuck = (
            db.query(BenchmarkRun)
            .filter(BenchmarkRun.status.in_(["queued", "running"]))
            .all()
        )
        for run in stuck:
            run.status = "failed"
            run.error = "Run interrupted by a service restart"
            run.completed_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _reap_interrupted_runs()
    yield


app = FastAPI(
    title="Fieldproxy AgentBench API",
    description=(
        "Regression-testing backend for field-service AI agents. "
        "Executes benchmark runs for real: the dispatch agent runs each "
        "scenario against seeded world data and every decision is checked "
        "by deterministic evaluation rules."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
