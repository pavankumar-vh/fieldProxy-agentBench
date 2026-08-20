from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BenchmarkRun, CaseResult, RegressionReport, TestCase
from app.repositories import run_detail_out, run_out, test_case_out
from app.schemas import BenchmarkRunOut, RunDetailOut, TestCaseOut

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[BenchmarkRunOut])
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(BenchmarkRun).order_by(BenchmarkRun.started_at.desc()).all()
    return [run_out(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunDetailOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run_detail_out(db, run)


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Remove a run with its case results and reports (admin cleanup)."""
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if (
        db.query(RegressionReport)
        .filter(RegressionReport.baseline_run_id == run_id)
        .count()
    ):
        raise HTTPException(
            status_code=409, detail="Run is a regression baseline and cannot be deleted"
        )
    db.query(RegressionReport).filter(RegressionReport.run_id == run_id).delete()
    db.query(CaseResult).filter(CaseResult.run_id == run_id).delete()
    db.delete(run)
    db.commit()


@router.get("/test-cases", response_model=list[TestCaseOut])
def list_test_cases(db: Session = Depends(get_db)):
    cases = db.query(TestCase).order_by(TestCase.id).all()
    return [test_case_out(db, tc) for tc in cases]
