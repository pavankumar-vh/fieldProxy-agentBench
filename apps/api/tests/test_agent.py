"""Agent behaviour tests — the same world, different policies."""

from datetime import UTC, datetime

from app.database import SessionLocal
from app.models import TestCase
from app.services.agent import DispatchAgent
from app.services.world import build_world, resolve_tree

STRICT = {}
V1_2 = {
    "validate_technician_id": False,
    "enforce_cert_expiry": False,
    "escalate_on_sla_breach": False,
}


def run_case(case_id: str, policy: dict):
    db = SessionLocal()
    try:
        tc = db.get(TestCase, case_id)
        ref = datetime.now(UTC)
        spec = tc.spec
        world = build_world(db, ref, spec.get("world_overrides"))
        request = resolve_tree(dict(spec["request"]), ref)
        request["_now"] = ref
        agent = DispatchAgent(world, policy, ref)
        return agent.run(request), agent
    finally:
        db.close()


def test_strict_agent_assigns_emergency_ac_repair():
    decision, agent = run_case("tc_001", STRICT)
    assert decision["action"] == "assign"
    assert decision["technician_id"] == "tech_007"
    # The trace must contain real steps with measured latencies.
    assert len(agent.steps) >= 4
    assert all(s["latency_ms"] >= 1 for s in agent.steps)
    assert agent.steps[0]["type"] == "intent_parsing"
    assert agent.steps[-1]["type"] == "decision"


def test_strict_agent_rejects_expired_certification():
    decision, _ = run_case("tc_002", STRICT)
    assert decision["action"] == "reject"
    assert "expired" in decision["reason"].lower()


def test_buggy_agent_accepts_expired_certification():
    """v1.2's missing expiry enforcement produces a genuinely different result."""
    decision, _ = run_case("tc_002", V1_2)
    assert decision["action"] == "assign"
    assert decision["technician_id"] == "tech_003"


def test_strict_agent_escalates_sla_breach():
    decision, _ = run_case("tc_006", STRICT)
    assert decision["action"] == "escalate"


def test_buggy_agent_ignores_sla_breach():
    decision, _ = run_case("tc_006", V1_2)
    assert decision["action"] == "assign"


def test_strict_agent_rejects_unknown_technician():
    decision, _ = run_case("tc_010", STRICT)
    assert decision["action"] == "reject"


def test_buggy_agent_skips_id_validation():
    decision, _ = run_case("tc_010", V1_2)
    assert decision["action"] == "assign"


def test_outside_working_hours_proposes_next_slot():
    decision, _ = run_case("tc_009", STRICT)
    assert decision["action"] == "propose_slot"
    assert decision["scheduled_at"]


def test_mutation_blocked_tech_finds_alternative():
    decision, _ = run_case("tc_013", STRICT)
    assert decision["action"] == "assign"
    assert decision["technician_id"] != "tech_007"


def test_mutation_empty_inventory_defers():
    decision, _ = run_case("tc_012", STRICT)
    assert decision["action"] == "defer"
