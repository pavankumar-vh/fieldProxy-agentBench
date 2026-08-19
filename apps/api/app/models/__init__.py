"""SQLAlchemy ORM models for AgentBench."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(120))
    # Hash of the agent policy — changes whenever agent behaviour changes.
    prompt_hash: Mapped[str] = mapped_column(String(16))
    # Real behavioural config: which checks/steps this agent version executes.
    policy: Mapped[dict] = mapped_column(JSON, default=dict)
    # "policy" = deterministic rule engine, "gemini" = real LLM tool loop.
    engine: Mapped[str] = mapped_column(String(16), default="policy", server_default="policy")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    runs: Mapped[list["BenchmarkRun"]] = relationship(back_populates="agent_version")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(32))
    scenario: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    expected_outcome: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_mutation: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Machine-readable scenario: job request, world overrides, evaluation checks.
    spec: Mapped[dict] = mapped_column(JSON, default=dict)


class Technician(Base):
    """World data the agent's tools query at runtime."""

    __tablename__ = "technicians"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    working_start: Mapped[str] = mapped_column(String(5), default="08:00")
    working_end: Mapped[str] = mapped_column(String(5), default="18:00")
    # [{skill: "HVAC_CERT", cert_expiry: "<ISO date or offset token>"}]
    skills: Mapped[list] = mapped_column(JSON, default=list)

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="technician"
    )
    inventory: Mapped[list["TechnicianInventory"]] = relationship(
        back_populates="technician"
    )


class TechnicianInventory(Base):
    __tablename__ = "technician_inventory"

    technician_id: Mapped[str] = mapped_column(
        ForeignKey("technicians.id"), primary_key=True
    )
    part_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    technician: Mapped[Technician] = relationship(back_populates="inventory")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    technician_id: Mapped[str] = mapped_column(ForeignKey("technicians.id"))
    # Start stored as a time token (resolved per-run); the end is derived
    # from the duration so both ends stay consistent.
    start_at: Mapped[str] = mapped_column(String(40))
    duration_hours: Mapped[float] = mapped_column(Float, default=1.0)

    technician: Mapped[Technician] = relationship(back_populates="appointments")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_version_id: Mapped[str] = mapped_column(ForeignKey("agent_versions.id"))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    benchmark_type: Mapped[str] = mapped_column(String(32), default="full")
    mutation_testing: Mapped[bool] = mapped_column(Boolean, default=False)
    compare_against: Mapped[str | None] = mapped_column(String(32), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(64), default="manual")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Totals written when the run completes.
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    critical_failures: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)

    agent_version: Mapped[AgentVersion] = relationship(back_populates="runs")
    results: Mapped[list["CaseResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CaseResult(Base):
    """One executed test case inside a run — real trace, decision and evaluation."""

    __tablename__ = "case_results"
    __table_args__ = (UniqueConstraint("run_id", "test_case_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"))
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"))
    result: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    agent_request: Mapped[str] = mapped_column(Text, default="")
    agent_decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    evaluation: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[BenchmarkRun] = relationship(back_populates="results")
    test_case: Mapped[TestCase] = relationship()


class RegressionReport(Base):
    __tablename__ = "regression_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"))
    baseline_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("benchmark_runs.id"), nullable=True
    )
    agent_name: Mapped[str] = mapped_column(String(120))
    baseline_version: Mapped[str] = mapped_column(String(32))
    current_version: Mapped[str] = mapped_column(String(32))
    baseline_pass_rate: Mapped[float] = mapped_column(Float)
    current_pass_rate: Mapped[float] = mapped_column(Float)
    delta: Mapped[float] = mapped_column(Float)
    regression_detected: Mapped[bool] = mapped_column(Boolean)
    critical_regressions: Mapped[int] = mapped_column(Integer, default=0)
    new_failure_ids: Mapped[list] = mapped_column(JSON, default=list)
    fixed_test_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
