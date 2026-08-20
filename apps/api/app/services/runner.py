"""Benchmark execution: runs the agent over selected test cases, evaluates
every decision, persists real results, and produces regression reports."""

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AgentVersion,
    BenchmarkRun,
    CaseResult,
    RegressionReport,
    TestCase,
)
from app.services.agent import DispatchAgent
from app.services.evaluator import evaluate
from app.services.gemini import GeminiAgent
from app.services.groq import GroqAgent
from app.services.langgraph_agent import LangGraphAgent
from app.services.world import build_world, resolve_tree

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def make_agent(agent_version: AgentVersion, world: dict, ref: datetime):
    """Instantiate the right engine for this agent version."""
    engine = agent_version.engine
    if engine in ("gemini", "langgraph", "groq"):
        settings = get_settings()
        if engine == "groq":
            return GroqAgent(
                world,
                agent_version.policy,
                ref,
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                model=agent_version.model,
            )
        cls = LangGraphAgent if engine == "langgraph" else GeminiAgent
        return cls(
            world,
            agent_version.policy,
            ref,
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=agent_version.model,
        )
    return DispatchAgent(world, agent_version.policy, ref)


def select_cases(db: Session, benchmark_type: str, mutation_testing: bool) -> list[TestCase]:
    cases = list(db.query(TestCase).order_by(TestCase.id).all())
    if benchmark_type == "dispatch":
        cases = [c for c in cases if c.category == "dispatch"]
    elif benchmark_type == "critical":
        cases = [c for c in cases if c.severity == "critical"]
    elif benchmark_type == "mutations":
        cases = [c for c in cases if c.is_mutation]
    if benchmark_type != "mutations" and not mutation_testing:
        cases = [c for c in cases if not c.is_mutation]
    return cases


def execute_case(
    db: Session, agent_version: AgentVersion, test_case: TestCase, ref: datetime
) -> CaseResult:
    """Run one test case for real: build world, run agent, evaluate."""
    spec = test_case.spec or {}
    world = build_world(db, ref, spec.get("world_overrides"))

    # Resolve the job request's time tokens against this run's start time.
    request = resolve_tree(dict(spec.get("request", {})), ref)
    request["_now"] = ref
    request.setdefault("request_text", spec.get("request_text", test_case.scenario))

    agent = make_agent(agent_version, world, ref)
    started = time.perf_counter()
    error = None
    decision: dict | None = None
    try:
        decision = agent.run(request)
    except Exception as exc:
        error = str(exc)
    latency_ms = max(1, round((time.perf_counter() - started) * 1000))

    if error:
        evaluation: list[dict] = []
        result = "error"
    else:
        evaluation = evaluate(world, request, decision, spec.get("checks", []))
        result = "pass" if evaluation and all(e["passed"] for e in evaluation) else "fail"
        # Append an evaluation summary step to the trace.
        agent.steps.append(
            {
                "id": f"step_{uuid.uuid4().hex[:8]}",
                "step_index": len(agent.steps),
                "type": "evaluation",
                "name": "DETERMINISTIC VALIDATION",
                "input": None,
                "output": {
                    "passed": result == "pass",
                    "checks": len(evaluation),
                    "failures": sum(1 for e in evaluation if not e["passed"]),
                },
                "status": "pass" if result == "pass" else "fail",
                "latency_ms": 1,
                "error": None,
            }
        )

    return CaseResult(
        run_id="",
        test_case_id=test_case.id,
        result=result,
        latency_ms=latency_ms,
        agent_request=request.get("request_text", ""),
        agent_decision=decision,
        steps=agent.steps,
        evaluation=evaluation,
        error=error,
    )


def execute_run(db: Session, run: BenchmarkRun) -> BenchmarkRun:
    """Execute all selected cases for a run and persist real results."""
    agent_version = db.get(AgentVersion, run.agent_version_id)
    run.status = "running"
    db.commit()

    run_started = time.perf_counter()
    cases = select_cases(db, run.benchmark_type, run.mutation_testing)
    ref = run.started_at or datetime.now(UTC)

    passed = failed = critical_failures = 0
    for case in cases:
        cr = execute_case(db, agent_version, case, ref)
        cr.run_id = run.id
        db.add(cr)
        if cr.result == "pass":
            passed += 1
        else:
            failed += 1
            if case.severity == "critical":
                critical_failures += 1

    total = len(cases)
    run.total_tests = total
    run.passed = passed
    run.failed = failed
    run.critical_failures = critical_failures
    run.pass_rate = round(passed / total * 100, 1) if total else 0.0
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.duration_ms = round((time.perf_counter() - run_started) * 1000)
    db.commit()

    if run.compare_against:
        build_regression_report(db, run)
    return run


def _latest_completed_run(db: Session, agent_name: str, version: str) -> BenchmarkRun | None:
    stmt = (
        select(BenchmarkRun)
        .join(AgentVersion, BenchmarkRun.agent_version_id == AgentVersion.id)
        .where(
            AgentVersion.name == agent_name,
            AgentVersion.version == version,
            BenchmarkRun.status == "completed",
        )
        .order_by(BenchmarkRun.completed_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def build_regression_report(db: Session, run: BenchmarkRun) -> RegressionReport | None:
    """Compare this run against the latest completed baseline-version run."""
    current_version = db.get(AgentVersion, run.agent_version_id)
    # Safety net: a version can never be its own baseline.
    if run.compare_against == current_version.version:
        return None
    baseline_run = _latest_completed_run(
        db, current_version.name, run.compare_against
    )
    if baseline_run is None:
        return None

    current_results = {r.test_case_id: r for r in run.results}
    baseline_results = {r.test_case_id: r for r in baseline_run.results}

    new_failures, fixed = [], []
    for tc_id, cr in current_results.items():
        base = baseline_results.get(tc_id)
        if base is None:
            continue
        if cr.result != "pass" and base.result == "pass":
            new_failures.append(tc_id)
        elif cr.result == "pass" and base.result != "pass":
            fixed.append(tc_id)

    cases_by_id = {c.id: c for c in db.query(TestCase).all()}
    critical = sum(
        1 for tc_id in new_failures if cases_by_id[tc_id].severity == "critical"
    )

    report = RegressionReport(
        id=new_id("reg"),
        run_id=run.id,
        baseline_run_id=baseline_run.id,
        agent_name=current_version.name,
        baseline_version=run.compare_against,
        current_version=current_version.version,
        baseline_pass_rate=baseline_run.pass_rate,
        current_pass_rate=run.pass_rate,
        delta=round(run.pass_rate - baseline_run.pass_rate, 1),
        regression_detected=run.pass_rate < baseline_run.pass_rate,
        critical_regressions=critical,
        new_failure_ids=new_failures,
        fixed_test_ids=fixed,
    )
    db.add(report)
    db.commit()
    return report
