"""Seed script: loads world data and test scenarios from scenarios/,
registers agent versions, then executes real benchmark runs so the UI
starts with genuine results.

Run from apps/api:  python -m scripts.seed
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models import (
    AgentVersion,
    Appointment,
    BenchmarkRun,
    CaseResult,
    RegressionReport,
    Technician,
    TechnicianInventory,
    TestCase,
)
from app.services.runner import execute_run, new_id

# Overridable so container images can place scenarios anywhere.
REPO_ROOT = Path(os.environ.get("AGENTBENCH_REPO_ROOT") or Path(__file__).resolve().parents[3])
WORLD_PATH = REPO_ROOT / "scenarios" / "fixtures" / "world.json"
CASES_PATH = REPO_ROOT / "scenarios" / "dispatch" / "test_cases.json"

# Agent versions differ only in policy — that is what the benchmark measures.
AGENT_VERSIONS = [
    {
        "id": "av_003",
        "version": "v1.0",
        "model": "gemini-1.5-pro",
        "status": "deprecated",
        "description": (
            "Initial prototype. Skips certification-expiry, inventory and "
            "schedule enforcement — multiple critical edge-case failures."
        ),
        "policy": {
            "enforce_cert_expiry": False,
            "enforce_inventory": False,
            "enforce_schedule": False,
        },
    },
    {
        "id": "av_002",
        "version": "v1.1",
        "model": "gemini-2.0-flash",
        "status": "deprecated",
        "description": (
            "Stable version with full enforcement of certification, "
            "inventory, schedule, working-hours and SLA rules."
        ),
        "policy": {},
    },
    {
        "id": "av_001",
        "version": "v1.2",
        "model": "gemini-2.0-flash",
        "status": "active",
        "description": (
            "Latest version. Introduced regressions: skips technician-ID "
            "validation, ignores certification expiry, and no longer "
            "escalates SLA breaches."
        ),
        "policy": {
            "validate_technician_id": False,
            "enforce_cert_expiry": False,
            "escalate_on_sla_breach": False,
        },
    },
    {
        "id": "av_004",
        "version": "v2.0-llm",
        "model": "gemini-2.0-flash",
        "status": "draft",
        "engine": "gemini",
        "description": (
            "Real LLM agent: Gemini function-calling loop over the same six "
            "tools. Requires GEMINI_API_KEY — without it, cases report an "
            "honest error instead of a fake result."
        ),
        "policy": {},
    },
    {
        "id": "av_005",
        "version": "v2.1-graph",
        "model": "gemini-2.0-flash",
        "status": "draft",
        "engine": "langgraph",
        "description": (
            "Phase 3: the same Gemini tool loop expressed as an explicit "
            "LangGraph state machine (model → tools → model). Same tools, "
            "same grading — comparable traces across engines."
        ),
        "policy": {},
    },
]


def policy_hash(policy: dict) -> str:
    canonical = json.dumps(policy, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:6]


def wipe(db) -> None:
    for model in (
        RegressionReport,
        CaseResult,
        BenchmarkRun,
        AgentVersion,
        TestCase,
        Appointment,
        TechnicianInventory,
        Technician,
    ):
        db.query(model).delete()
    db.commit()


def seed_world(db) -> None:
    world = json.loads(WORLD_PATH.read_text())
    for tech in world["technicians"]:
        db.add(
            Technician(
                id=tech["id"],
                name=tech["name"],
                lat=tech["lat"],
                lng=tech["lng"],
                working_start=tech.get("working_start", "06:00"),
                working_end=tech.get("working_end", "22:00"),
                skills=tech.get("skills", []),
            )
        )
        for part_id, qty in tech.get("inventory", {}).items():
            db.add(
                TechnicianInventory(
                    technician_id=tech["id"], part_id=part_id, quantity=qty
                )
            )
        for appt in tech.get("appointments", []):
            db.add(
                Appointment(
                    technician_id=tech["id"],
                    start_at=appt["start_at"],
                    duration_hours=appt.get("duration_hours", 1.0),
                )
            )
    db.commit()


def seed_test_cases(db) -> None:
    cases = json.loads(CASES_PATH.read_text())
    for case in cases:
        spec = case.pop("spec")
        db.add(TestCase(spec=spec, **case))
    db.commit()


def seed_agent_versions(db) -> None:
    for av in AGENT_VERSIONS:
        db.add(
            AgentVersion(
                id=av["id"],
                name="Dispatch Agent",
                version=av["version"],
                model=av["model"],
                prompt_hash=policy_hash(av["policy"]),
                policy=av["policy"],
                engine=av.get("engine", "policy"),
                status=av["status"],
                description=av["description"],
            )
        )
    db.commit()


def run_benchmark(
    db, agent_version_id: str, compare_against: str | None = None
) -> BenchmarkRun:
    run = BenchmarkRun(
        id=new_id("run"),
        agent_version_id=agent_version_id,
        status="queued",
        benchmark_type="full",
        mutation_testing=True,
        compare_against=compare_against,
        triggered_by="seed",
    )
    db.add(run)
    db.commit()
    return execute_run(db, run)


def main() -> None:
    db = SessionLocal()
    try:
        # Container boot mode: never wipe a persisted database, only seed
        # a fresh one (e.g. Render Postgres on first start).
        if "--if-empty" in sys.argv and db.query(TestCase).count() > 0:
            print("→ Database already seeded — skipping.")
            return

        print("→ Wiping existing data…")
        wipe(db)
        print("→ Seeding world (technicians, inventory, appointments)…")
        seed_world(db)
        print("→ Seeding test cases…")
        seed_test_cases(db)
        print("→ Seeding agent versions…")
        seed_agent_versions(db)

        print("→ Executing benchmark: Dispatch Agent v1.0…")
        r0 = run_benchmark(db, "av_003")
        print(f"  {r0.passed}/{r0.total_tests} passed ({r0.pass_rate}%)")

        print("→ Executing benchmark: Dispatch Agent v1.1…")
        r1 = run_benchmark(db, "av_002")
        print(f"  {r1.passed}/{r1.total_tests} passed ({r1.pass_rate}%)")

        print("→ Executing benchmark: Dispatch Agent v1.2 vs v1.1…")
        r2 = run_benchmark(db, "av_001", compare_against="v1.1")
        print(f"  {r2.passed}/{r2.total_tests} passed ({r2.pass_rate}%)")

        # The LLM version is only executed when a real API key is present —
        # otherwise we register it without fabricating results.
        if os.environ.get("GEMINI_API_KEY"):
            print("→ Executing benchmark: Dispatch Agent v2.0-llm (Gemini)…")
            r3 = run_benchmark(db, "av_004", compare_against="v1.1")
            print(f"  {r3.passed}/{r3.total_tests} passed ({r3.pass_rate}%)")
        else:
            print("→ Skipping v2.0-llm run (set GEMINI_API_KEY to execute it).")

        reports = db.query(RegressionReport).count()
        print(f"✓ Seed complete: {reports} regression report(s) generated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
