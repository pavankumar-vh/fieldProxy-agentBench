"""The Dispatch Agent — a real, executable policy that schedules field
technicians by calling tools against the world snapshot.

Every agent version runs the same tool loop; versions differ only in their
`policy` (which validations/enforcements are active). That is what makes
benchmark comparisons between versions meaningful: behavioural differences
produce genuinely different results.

Each step is recorded with its real measured latency.
"""

import math
import time
import uuid
from datetime import datetime, timedelta

DEFAULT_POLICY = {
    "validate_technician_id": True,
    "enforce_cert_expiry": True,
    "cert_expiry_grace_days": 0,
    "enforce_inventory": True,
    "enforce_schedule": True,
    "enforce_working_hours": True,
    "escalate_on_sla_breach": True,
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _within_working_hours(tech: dict, at: datetime) -> bool:
    hm = at.strftime("%H:%M")
    return tech["working_start"] <= hm < tech["working_end"]


def _conflicts(tech: dict, start: datetime, end: datetime) -> list[dict]:
    out = []
    for appt in tech["appointments"]:
        a_start, a_end = appt["start_at"], appt["end_at"]
        if start < a_end and end > a_start:
            out.append(appt)
    return out


class DispatchAgent:
    """Deterministic tool-using agent. The policy decides what it enforces."""

    def __init__(self, world: dict, policy: dict, now: datetime):
        self.world = world
        self.policy = {**DEFAULT_POLICY, **(policy or {})}
        self.now = now
        self.steps: list[dict] = []

    # ── step recording ────────────────────────────────────────────────
    def _record(self, type_: str, name: str, fn, input_: dict | None = None):
        started = time.perf_counter()
        try:
            output = fn()
            status = "pass"
            error = None
        except Exception as exc:  # tool errors are part of the trace too
            output = None
            status = "fail"
            error = str(exc)
        latency_ms = max(1, round((time.perf_counter() - started) * 1000))
        self.steps.append(
            {
                "id": f"step_{uuid.uuid4().hex[:8]}",
                "step_index": len(self.steps),
                "type": type_,
                "name": name,
                "input": input_,
                "output": output,
                "status": status,
                "latency_ms": latency_ms,
                "error": error,
            }
        )
        if error:
            raise RuntimeError(error)
        return output

    # ── tools ─────────────────────────────────────────────────────────
    def _tool_find_technician(self, technician_id: str) -> dict:
        tech = self.world["technicians"].get(technician_id)
        return {"exists": tech is not None, "technician_id": technician_id}

    def _tool_find_available(self, skill: str, requested_at: datetime,
                             location: dict) -> dict:
        found = []
        for tech in self.world["technicians"].values():
            if skill and skill not in tech["skills"]:
                continue
            dist = _haversine_km(
                location["lat"], location["lng"], tech["lat"], tech["lng"]
            )
            found.append(
                {"id": tech["id"], "name": tech["name"], "distance_km": round(dist, 1)}
            )
        found.sort(key=lambda t: t["distance_km"])
        return {"technicians": found}

    def _tool_check_skills(self, technician_id: str, required: list[str]) -> dict:
        tech = self.world["technicians"][technician_id]
        details = {}
        for skill in required:
            entry = tech["skills"].get(skill)
            if entry is None:
                details[skill] = {"certified": False, "reason": "skill not held"}
            else:
                expiry = entry.get("cert_expiry")
                details[skill] = {
                    "certified": True,
                    "cert_expiry": expiry.isoformat() if isinstance(expiry, datetime) else expiry,
                }
        return {"technician_id": technician_id, "skills": details}

    def _tool_check_inventory(self, technician_id: str, parts: list[str]) -> dict:
        tech = self.world["technicians"][technician_id]
        out = {}
        for part in parts:
            qty = tech["inventory"].get(part, 0)
            out[part] = {"available": qty > 0, "quantity": qty}
        return {"technician_id": technician_id, "parts": out}

    def _tool_check_schedule(self, technician_id: str, requested_at: datetime,
                             duration_hours: float) -> dict:
        tech = self.world["technicians"][technician_id]
        end = requested_at + timedelta(hours=duration_hours)
        conflicts = _conflicts(tech, requested_at, end)
        result = {
            "technician_id": technician_id,
            "available": not conflicts and _within_working_hours(tech, requested_at),
        }
        if conflicts:
            result["next_slot"] = self._next_slot(tech, requested_at, duration_hours)
        return result

    def _tool_check_sla(self, job_type: str, urgency: str,
                        requested_at: datetime) -> dict:
        sla_hours = self.world["sla_dispatch_hours"].get(urgency, 72)
        deadline = self.now + timedelta(hours=sla_hours)
        return {
            "job_type": job_type,
            "urgency": urgency,
            "sla_hours": sla_hours,
            "deadline": deadline.isoformat(),
            "within_sla": requested_at <= deadline,
        }

    def _next_slot(self, tech: dict, after: datetime, duration_hours: float) -> str:
        """Scan forward for the next conflict-free slot inside working hours."""
        candidate = after.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        horizon = after + timedelta(days=7)
        while candidate < horizon:
            end = candidate + timedelta(hours=duration_hours)
            if (
                _within_working_hours(tech, candidate)
                and not _conflicts(tech, candidate, end)
            ):
                return candidate.isoformat()
            candidate += timedelta(minutes=30)
        return None  # pragma: no cover - horizon is generous

    # ── cert-expiry gate (policy-controlled) ──────────────────────────
    def _cert_ok(self, tech: dict, required: list[str], at: datetime) -> tuple[bool, str]:
        if not self.policy["enforce_cert_expiry"]:
            return True, "cert expiry enforcement disabled by policy"
        grace = timedelta(days=self.policy["cert_expiry_grace_days"])
        for skill in required:
            entry = tech["skills"].get(skill)
            expiry = entry.get("cert_expiry") if entry else None
            if isinstance(expiry, datetime) and expiry + grace < at:
                return False, f"{skill} expired {expiry.date().isoformat()}"
        return True, ""

    # ── main run ──────────────────────────────────────────────────────
    def run(self, request: dict) -> dict:
        """Execute the dispatch policy. Returns the decision dict."""
        p = self.policy

        intent = self._record(
            "intent_parsing",
            "INTENT PARSING",
            lambda: {
                "intent": "schedule_job",
                "job_type": request["job_type"],
                "urgency": request["urgency"],
                "requested_time": request["requested_at"].isoformat(),
                "required_skills": request.get("required_skills", []),
                "required_parts": request.get("required_parts", []),
                "preferred_technician": request.get("preferred_technician_id"),
            },
            {"raw_request": request.get("request_text", "")},
        )

        decision: dict = {"action": None, "technician_id": None,
                          "scheduled_at": None, "reason": ""}
        inventory_blocked = False
        requested_at = request["requested_at"]
        duration = request.get("duration_hours", 2)
        skills = request.get("required_skills", [])
        parts = request.get("required_parts", [])
        location = request.get("location", {"lat": 12.9716, "lng": 77.5946})

        # Preferred technician path (customer requested someone specific).
        preferred = request.get("preferred_technician_id")
        if preferred:
            lookup = self._record(
                "tool_call",
                f"find_technician({preferred})",
                lambda: self._tool_find_technician(preferred),
                {"technician_id": preferred},
            )
            if not lookup["exists"]:
                if p["validate_technician_id"]:
                    decision.update(
                        action="reject",
                        reason=f"Validation error — technician {preferred} not found",
                    )
                    return self._finalize(decision, intent, request)
                # Buggy policy: silently ignore the bad ID and search anyway.
                preferred = None

        if preferred:
            candidates = [preferred]
        else:
            found = self._record(
                "tool_call",
                f"find_available_technicians({skills[0] if skills else 'ANY'})",
                lambda: self._tool_find_available(
                    skills[0] if skills else "", requested_at, location
                ),
                {"skill": skills[0] if skills else None,
                 "requested_at": requested_at.isoformat(), "location": location},
            )
            candidates = [t["id"] for t in found["technicians"]][:5]

        # SLA check applies to the request itself.
        sla = self._record(
            "tool_call",
            "check_sla()",
            lambda: self._tool_check_sla(
                request["job_type"], request["urgency"], requested_at
            ),
            {"job_type": request["job_type"], "urgency": request["urgency"]},
        )
        # A buggy policy may proceed despite the breach.
        if not sla["within_sla"] and p["escalate_on_sla_breach"]:
            decision.update(
                action="escalate",
                reason=(
                    f"SLA breach — {request['urgency']} job requested beyond "
                    f"{sla['sla_hours']}h dispatch window; escalated to manager"
                ),
            )
            return self._finalize(decision, intent, request)

        for tech_id in candidates:
            tech = self.world["technicians"].get(tech_id)
            if tech is None:
                continue

            skill_out = self._record(
                "tool_call",
                f"check_skills({tech_id})",
                lambda tid=tech_id: self._tool_check_skills(tid, skills),
                {"technician_id": tech_id, "required_skills": skills},
            )
            if not all(d["certified"] for d in skill_out["skills"].values()):
                continue

            ok, why = self._cert_ok(tech, skills, requested_at)
            if not ok:
                if preferred:
                    decision.update(
                        action="reject",
                        reason=f"Assignment rejected — {why}",
                    )
                    return self._finalize(decision, intent, request)
                continue

            if parts and p["enforce_inventory"]:
                inv = self._record(
                    "tool_call",
                    f"check_inventory({tech_id})",
                    lambda tid=tech_id: self._tool_check_inventory(tid, parts),
                    {"technician_id": tech_id, "parts": parts},
                )
                if not all(v["available"] for v in inv["parts"].values()):
                    if preferred:
                        decision.update(
                            action="defer",
                            reason="Job deferred — required part out of stock",
                        )
                        return self._finalize(decision, intent, request)
                    inventory_blocked = True
                    continue

            if p["enforce_working_hours"] and not _within_working_hours(tech, requested_at):
                continue

            if p["enforce_schedule"]:
                sched = self._record(
                    "tool_call",
                    f"check_schedule({tech_id})",
                    lambda tid=tech_id: self._tool_check_schedule(
                        tid, requested_at, duration
                    ),
                    {"technician_id": tech_id,
                     "requested_at": requested_at.isoformat(),
                     "duration_hours": duration},
                )
                if not sched["available"]:
                    if preferred:
                        decision.update(
                            action="propose_slot",
                            scheduled_at=sched.get("next_slot"),
                            reason=(
                                f"Conflict detected for {tech_id} — alternative "
                                f"slot proposed"
                            ),
                        )
                        return self._finalize(decision, intent, request)
                    continue

            decision.update(
                action="assign",
                technician_id=tech_id,
                scheduled_at=requested_at.isoformat(),
                reason=f"All checks passed. {tech['name']} assigned.",
            )
            return self._finalize(decision, intent, request)

        # No candidate survived the gates.
        if inventory_blocked:
            decision.update(
                action="defer",
                reason="Job deferred — required part unavailable for all candidates",
            )
        elif p["enforce_working_hours"] and not any(
            _within_working_hours(t, requested_at)
            for t in self.world["technicians"].values()
        ):
            any_tech = next(iter(self.world["technicians"].values()))
            decision.update(
                action="propose_slot",
                scheduled_at=self._next_slot(any_tech, requested_at, duration),
                reason="Outside working hours — next-day slot proposed",
            )
        else:
            decision.update(
                action="escalate",
                reason="No technician available — escalation triggered",
            )
        return self._finalize(decision, intent, request)


    def _finalize(self, decision: dict, intent: dict, request: dict) -> dict:
        self._record(
            "decision",
            "AGENT DECISION",
            lambda: decision,
            None,
        )
        return decision
