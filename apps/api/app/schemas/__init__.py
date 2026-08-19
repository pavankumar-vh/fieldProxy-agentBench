"""Pydantic schemas — field names match apps/web/lib/types.ts exactly."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

AgentStatus = Literal["active", "deprecated", "draft"]
RunStatus = Literal["queued", "running", "completed", "failed"]
TestResult = Literal["pass", "fail", "error", "skipped"]
Severity = Literal["critical", "high", "medium", "low"]


class AgentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    model: str
    engine: str = "policy"
    prompt_hash: str
    pass_rate: float
    total_tests: int
    passed: int
    failed: int
    critical_failures: int
    status: AgentStatus
    created_at: datetime
    description: str | None = None


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    scenario: str
    description: str
    expected_outcome: str
    severity: Severity
    last_result: TestResult | None = None
    last_run_at: datetime | None = None
    tags: list[str] = []
    is_mutation: bool = False
    parent_id: str | None = None


class BenchmarkRunOut(BaseModel):
    id: str
    agent_version_id: str
    agent_name: str
    agent_version: str
    status: RunStatus
    total_tests: int
    passed: int
    failed: int
    critical_failures: int
    pass_rate: float
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    mutation_testing: bool
    compare_against: str | None = None
    triggered_by: str


class AgentStepOut(BaseModel):
    id: str
    step_index: int
    type: str
    name: str
    input: dict | None = None
    output: dict | None = None
    status: str
    latency_ms: int | None = None
    error: str | None = None


class EvaluationResultOut(BaseModel):
    rule: str
    passed: bool
    severity: Severity
    expected: str
    actual: str
    reason: str


class RunDetailOut(BenchmarkRunOut):
    test_case: TestCaseOut
    steps: list[AgentStepOut] = []
    evaluation: list[EvaluationResultOut] = []
    agent_request: str
    agent_decision: dict | None = None
    latency_ms: int = 0
    error: str | None = None


class RegressionReportOut(BaseModel):
    id: str
    agent_name: str
    baseline_version: str
    current_version: str
    baseline_pass_rate: float
    current_pass_rate: float
    delta: float
    regression_detected: bool
    new_failures: list[TestCaseOut] = []
    fixed_tests: list[TestCaseOut] = []
    critical_regressions: int
    created_at: datetime


class DashboardMetricsOut(BaseModel):
    agent_reliability: float
    total_test_cases: int
    passed: int
    failed: int
    critical: int
    last_run_at: datetime | None = None
    active_agents: int
    total_runs: int


class BenchmarkRunRequest(BaseModel):
    agent_version_id: str
    benchmark_type: str = "full"
    mutation_testing: bool = False
    compare_against: str | None = None


class BenchmarkRunStarted(BaseModel):
    run_id: str
