from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import AgentVersion, BenchmarkRun, RegressionReport
from app.repositories import regression_report_out
from app.schemas import (
    BenchmarkRunRequest,
    BenchmarkRunStarted,
    RegressionReportOut,
)
from app.services.runner import execute_run, new_id

router = APIRouter(tags=["benchmark"])

VALID_TYPES = {"full", "dispatch", "critical", "mutations"}


def _execute_in_background(run_id: str) -> None:
    """Worker for LLM benchmarks — uses its own session, outlives the HTTP request."""
    db = SessionLocal()
    try:
        run = db.get(BenchmarkRun, run_id)
        if run is not None:
            execute_run(db, run)
    finally:
        db.close()


@router.post("/benchmark/run", response_model=BenchmarkRunStarted, status_code=201)
def start_benchmark(
    req: BenchmarkRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    agent_version = db.get(AgentVersion, req.agent_version_id)
    if agent_version is None:
        raise HTTPException(
            status_code=404, detail=f"Agent {req.agent_version_id} not found"
        )
    if req.benchmark_type not in VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"benchmark_type must be one of {sorted(VALID_TYPES)}",
        )
    if req.compare_against and req.compare_against == agent_version.version:
        raise HTTPException(
            status_code=422,
            detail="compare_against must differ from the benchmarked version "
            "— a version cannot regress against itself",
        )
    # One benchmark at a time: concurrent runs would hammer the free-tier
    # LLM quota and starve each other.
    active = (
        db.query(BenchmarkRun)
        .filter(BenchmarkRun.status.in_(["queued", "running"]))
        .count()
    )
    if active:
        raise HTTPException(
            status_code=409,
            detail="A benchmark is already running — wait for it to finish",
        )

    run = BenchmarkRun(
        id=new_id("run"),
        agent_version_id=req.agent_version_id,
        status="queued",
        benchmark_type=req.benchmark_type,
        mutation_testing=req.mutation_testing,
        compare_against=req.compare_against,
        triggered_by="manual",
    )
    db.add(run)
    db.commit()

    if agent_version.engine in ("gemini", "langgraph"):
        # LLM benchmarks take minutes (rate-limited Gemini round-trips).
        # Respond immediately and execute after the response.
        background_tasks.add_task(_execute_in_background, run.id)
    else:
        # Deterministic runs finish in ~1s — execute inline as before.
        execute_run(db, run)
    return BenchmarkRunStarted(run_id=run.id)


@router.get("/regressions", response_model=list[RegressionReportOut])
def list_regressions(db: Session = Depends(get_db)):
    reports = (
        db.query(RegressionReport).order_by(RegressionReport.created_at.desc()).all()
    )
    return [regression_report_out(db, r) for r in reports]
