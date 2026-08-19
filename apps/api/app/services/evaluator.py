"""Deterministic evaluation rules.

Each test case declares which rules to run (in its spec). Rules inspect the
agent's decision against the actual world state — no LLM judgement involved,
so results are fully reproducible.
"""

from datetime import datetime, timedelta

EvalCheck = dict  # {rule, passed, severity, expected, actual, reason}


def _iso(value) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _tech(world: dict, decision: dict) -> dict | None:
    tech_id = decision.get("technician_id")
    if not tech_id:
        return None
    return world["technicians"].get(tech_id)


def _scheduled_at(request: dict, decision: dict) -> datetime | None:
    raw = decision.get("scheduled_at")
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return request.get("requested_at")


def rule_outcome_is(world, request, decision, params) -> tuple[bool, str, str, str]:
    expected = params["action"]
    actual = decision.get("action")
    return (
        actual == expected,
        f"outcome '{expected}'",
        f"outcome '{actual}'",
        "Decision outcome matches scenario expectation"
        if actual == expected
        else f"Agent produced '{actual}' but scenario expects '{expected}'",
    )


def rule_technician_exists(world, request, decision, params) -> tuple[bool, str, str, str]:
    tech_id = decision.get("technician_id")
    if decision.get("action") != "assign":
        return True, "no assignment expected", f"action '{decision.get('action')}'", \
            "No assignment made — existence check not applicable"
    exists = tech_id in world["technicians"]
    return (
        exists,
        f"{tech_id} exists in database",
        f"{tech_id} found" if exists else f"{tech_id} not found",
        "Technician record found" if exists else "Assignment references unknown technician",
    )


def rule_technician_available(world, request, decision, params) -> tuple[bool, str, str, str]:
    tech = _tech(world, decision)
    if tech is None or decision.get("action") != "assign":
        return True, "no assignment expected", f"action '{decision.get('action')}'", \
            "No assignment made — availability check not applicable"
    start = _scheduled_at(request, decision)
    end = start + timedelta(hours=request.get("duration_hours", 2)) if start else None
    conflicts = []
    if start and end:
        for appt in tech["appointments"]:
            if start < appt["end_at"] and end > appt["start_at"]:
                conflicts.append(appt)
    return (
        not conflicts,
        f"Available at {_iso(start)}",
        "Available" if not conflicts else f"{len(conflicts)} conflicting appointment(s)",
        "No conflicting appointments" if not conflicts else "Technician double-booked",
    )


def rule_required_certification(world, request, decision, params) -> tuple[bool, str, str, str]:
    tech = _tech(world, decision)
    if tech is None or decision.get("action") != "assign":
        return True, "no assignment expected", f"action '{decision.get('action')}'", \
            "No assignment made — certification check not applicable"
    required = request.get("required_skills", [])
    missing = [s for s in required if s not in tech["skills"]]
    return (
        not missing,
        f"{', '.join(required) or 'no skills'} present",
        "All required certifications held" if not missing else f"missing {', '.join(missing)}",
        "Technician holds required certifications" if not missing else "Skill not held",
    )


def rule_certification_expiry(world, request, decision, params) -> tuple[bool, str, str, str]:
    tech = _tech(world, decision)
    if tech is None or decision.get("action") != "assign":
        return True, "no assignment expected", f"action '{decision.get('action')}'", \
            "No assignment made — expiry check not applicable"
    at = _scheduled_at(request, decision)
    expired = []
    for skill in request.get("required_skills", []):
        entry = tech["skills"].get(skill)
        expiry = entry.get("cert_expiry") if entry else None
        if isinstance(expiry, datetime) and at and expiry < at:
            expired.append(f"{skill} (expired {expiry.date().isoformat()})")
    return (
        not expired,
        "Cert expiry > scheduled date",
        "All certifications current" if not expired else ", ".join(expired),
        "Certification valid and not expired" if not expired else "Expired certification used",
    )


def rule_required_part(world, request, decision, params) -> tuple[bool, str, str, str]:
    tech = _tech(world, decision)
    if tech is None or decision.get("action") != "assign":
        return True, "no assignment expected", f"action '{decision.get('action')}'", \
            "No assignment made — inventory check not applicable"
    parts = request.get("required_parts", [])
    missing = [
        f"{part} (qty {tech['inventory'].get(part, 0)})"
        for part in parts
        if tech["inventory"].get(part, 0) <= 0
    ]
    return (
        not missing,
        f"{', '.join(parts) or 'no parts'} in inventory",
        "All parts in stock" if not missing else ", ".join(missing),
        "Part in stock" if not missing else "Part out of stock for assigned technician",
    )


def rule_sla_compliance(world, request, decision, params) -> tuple[bool, str, str, str]:
    if decision.get("action") != "assign":
        return True, "no schedule committed", f"action '{decision.get('action')}'", \
            "Agent did not commit a schedule — SLA check not applicable"
    urgency = request.get("urgency", "standard")
    sla_hours = world["sla_dispatch_hours"].get(urgency, 72)
    at = _scheduled_at(request, decision)
    now = request.get("_now")
    if at is None or now is None:
        return True, "n/a", "n/a", "SLA check not applicable"
    deadline = now + timedelta(hours=sla_hours)
    ok = at <= deadline
    return (
        ok,
        f"Dispatch within {sla_hours} hours",
        f"Scheduled {round((at - now).total_seconds() / 3600, 1)}h out" ,
        "SLA met" if ok else "Scheduled beyond SLA dispatch window",
    )


def rule_technician_not(world, request, decision, params) -> tuple[bool, str, str, str]:
    forbidden = params["technician_id"]
    actual = decision.get("technician_id")
    ok = actual != forbidden
    return (
        ok,
        f"assignment != {forbidden}",
        f"assigned {actual}" if actual else "no assignment",
        "Alternative technician used" if ok else "Forbidden technician was assigned",
    )


RULES = {
    "outcome_is": rule_outcome_is,
    "technician_exists": rule_technician_exists,
    "technician_available": rule_technician_available,
    "required_certification": rule_required_certification,
    "certification_expiry": rule_certification_expiry,
    "required_part": rule_required_part,
    "sla_compliance": rule_sla_compliance,
    "technician_not": rule_technician_not,
}


def evaluate(world: dict, request: dict, decision: dict, checks: list[dict]) -> list[EvalCheck]:
    """Run every declared check and return structured evaluation results."""
    results: list[EvalCheck] = []
    for check in checks:
        rule_name = check["rule"]
        rule_fn = RULES.get(rule_name)
        if rule_fn is None:
            results.append(
                {
                    "rule": rule_name,
                    "passed": False,
                    "severity": check.get("severity", "high"),
                    "expected": "unknown rule",
                    "actual": "rule not implemented",
                    "reason": f"No evaluator registered for '{rule_name}'",
                }
            )
            continue
        passed, expected, actual, reason = rule_fn(
            world, request, decision, check.get("params", {})
        )
        results.append(
            {
                "rule": rule_name,
                "passed": bool(passed),
                "severity": check.get("severity", "medium"),
                "expected": expected,
                "actual": actual,
                "reason": reason,
            }
        )
    return results
