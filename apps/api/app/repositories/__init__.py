"""Query helpers that turn ORM rows into API schemas.

Aggregate numbers (pass rates, last results, dashboard metrics) are always
derived from real stored run results — never hardcoded.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AgentVersion,
    BenchmarkRun,
    CaseResult,
    RegressionReport,
    TestCase,
)
from app.schemas import (
    AgentVersionOut,
    BenchmarkRunOut,
    DashboardMetricsOut,
    RegressionReportOut,
    RunDetailOut,
    TestCaseOut,
)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def latest_completed_run(db: Session, agent_version_id: str) -> BenchmarkRun | None:
    stmt = (
        select(BenchmarkRun)
        .where(
            BenchmarkRun.agent_version_id == agent_version_id,
            BenchmarkRun.status == "completed",
        )
        .order_by(BenchmarkRun.completed_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def last_case_result(db: Session, test_case_id: str) -> CaseResult | None:
    stmt = (
        select(CaseResult)
        .join(BenchmarkRun, CaseResult.run_id == BenchmarkRun.id)
        .where(CaseResult.test_case_id == test_case_id)
        .order_by(BenchmarkRun.started_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def agent_version_out(db: Session, av: AgentVersion) -> AgentVersionOut:
    run = latest_completed_run(db, av.id)
    return AgentVersionOut(
        id=av.id,
        name=av.name,
        version=av.version,
        model=av.model,
        engine=av.engine,
        prompt_hash=av.prompt_hash,
        pass_rate=run.pass_rate if run else 0.0,
        total_tests=run.total_tests if run else 0,
        passed=run.passed if run else 0,
        failed=run.failed if run else 0,
        critical_failures=run.critical_failures if run else 0,
        status=av.status,
        created_at=av.created_at,
        description=av.description,
    )


def test_case_out(db: Session, tc: TestCase) -> TestCaseOut:
    last = last_case_result(db, tc.id)
    last_run = db.get(BenchmarkRun, last.run_id) if last else None
    return TestCaseOut(
        id=tc.id,
        category=tc.category,
        scenario=tc.scenario,
        description=tc.description,
        expected_outcome=tc.expected_outcome,
        severity=tc.severity,
        last_result=last.result if last else None,
        last_run_at=last_run.started_at if last_run else None,
        tags=tc.tags or [],
        is_mutation=tc.is_mutation,
        parent_id=tc.parent_id,
    )


def run_out(run: BenchmarkRun) -> BenchmarkRunOut:
    av = run.agent_version
    return BenchmarkRunOut(
        id=run.id,
        agent_version_id=run.agent_version_id,
        agent_name=av.name,
        agent_version=av.version,
        status=run.status,
        total_tests=run.total_tests,
        passed=run.passed,
        failed=run.failed,
        critical_failures=run.critical_failures,
        pass_rate=run.pass_rate,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        mutation_testing=run.mutation_testing,
        compare_against=run.compare_against,
        triggered_by=run.triggered_by,
    )


def featured_result(db: Session, run: BenchmarkRun) -> CaseResult | None:
    """Pick the case result the run-detail page should feature: the most
    severe failure, or the first case if everything passed."""
    results = list(run.results)
    if not results:
        return None

    def sort_key(cr: CaseResult):
        tc = db.get(TestCase, cr.test_case_id)
        sev = SEVERITY_ORDER.get(tc.severity, 9) if tc else 9
        failed = 0 if cr.result != "pass" else 1
        return (failed, sev, cr.test_case_id)

    return min(results, key=sort_key)


def run_detail_out(db: Session, run: BenchmarkRun) -> RunDetailOut:
    cr = featured_result(db, run)
    tc = db.get(TestCase, cr.test_case_id) if cr else db.query(TestCase).first()
    base = run_out(run)
    return RunDetailOut(
        **base.model_dump(),
        test_case=test_case_out(db, tc),
        steps=cr.steps if cr else [],
        evaluation=cr.evaluation if cr else [],
        agent_request=cr.agent_request if cr else "",
        agent_decision=cr.agent_decision if cr else None,
        latency_ms=cr.latency_ms if cr else 0,
        error=cr.error if cr else run.error,
    )


def dashboard_metrics(db: Session) -> DashboardMetricsOut:
    active = db.query(AgentVersion).filter(AgentVersion.status == "active").first()
    last_run = None
    if active:
        last_run = latest_completed_run(db, active.id)
    if last_run is None:
        last_run = db.scalar(
            select(BenchmarkRun)
            .where(BenchmarkRun.status == "completed")
            .order_by(BenchmarkRun.completed_at.desc())
            .limit(1)
        )
    total_runs = db.scalar(
        select(func.count()).select_from(BenchmarkRun).where(
            BenchmarkRun.status == "completed"
        )
    )
    active_agents = db.scalar(
        select(func.count()).select_from(AgentVersion).where(
            AgentVersion.status == "active"
        )
    )
    return DashboardMetricsOut(
        agent_reliability=last_run.pass_rate if last_run else 0.0,
        total_test_cases=db.scalar(select(func.count()).select_from(TestCase)),
        passed=last_run.passed if last_run else 0,
        failed=last_run.failed if last_run else 0,
        critical=last_run.critical_failures if last_run else 0,
        last_run_at=last_run.completed_at if last_run else None,
        active_agents=active_agents or 0,
        total_runs=total_runs or 0,
    )


def regression_report_out(db: Session, report: RegressionReport) -> RegressionReportOut:
    cases_by_id = {c.id: c for c in db.query(TestCase).all()}
    new_failures = [
        test_case_out(db, cases_by_id[tc_id])
        for tc_id in report.new_failure_ids
        if tc_id in cases_by_id
    ]
    fixed = [
        test_case_out(db, cases_by_id[tc_id])
        for tc_id in report.fixed_test_ids
        if tc_id in cases_by_id
    ]
    return RegressionReportOut(
        id=report.id,
        agent_name=report.agent_name,
        baseline_version=report.baseline_version,
        current_version=report.current_version,
        baseline_pass_rate=report.baseline_pass_rate,
        current_pass_rate=report.current_pass_rate,
        delta=report.delta,
        regression_detected=report.regression_detected,
        new_failures=new_failures,
        fixed_tests=fixed,
        critical_regressions=report.critical_regressions,
        created_at=report.created_at,
    )
