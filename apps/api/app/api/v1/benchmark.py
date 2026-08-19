from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
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


@router.post("/benchmark/run", response_model=BenchmarkRunStarted, status_code=201)
def start_benchmark(req: BenchmarkRunRequest, db: Session = Depends(get_db)):
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

    # Real execution: the agent runs every selected case against the seeded
    # world and results are persisted. Deterministic and fast, so we execute
    # inline and return once the run is complete.
    execute_run(db, run)
    return BenchmarkRunStarted(run_id=run.id)


@router.get("/regressions", response_model=list[RegressionReportOut])
def list_regressions(db: Session = Depends(get_db)):
    reports = (
        db.query(RegressionReport).order_by(RegressionReport.created_at.desc()).all()
    )
    return [regression_report_out(db, r) for r in reports]
