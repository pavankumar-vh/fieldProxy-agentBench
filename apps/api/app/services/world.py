"""World state: load field-service world from the DB, apply scenario
mutations (overrides), and resolve relative time tokens against a run's
start time.

Time tokens allow benchmark scenarios to stay valid whenever they run:
  "now"           -> the reference time
  "now+18h"       -> reference + 18 hours  (also: now-30d, now+45m)
  "next@10:00"    -> next occurrence of 10:00 local, >= ref + 1h
  "next@10:00+2"  -> that occurrence, plus 2 whole days
Plain ISO timestamps are parsed as-is.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Appointment, Technician, TechnicianInventory

SLA_DISPATCH_HOURS = {"emergency": 24, "high": 48, "standard": 72}

_NOW_RE = re.compile(r"^now(?:(?P<sign>[+-])(?P<n>\d+)(?P<unit>[dhm]))?$")
_NEXT_RE = re.compile(r"^next@(?P<hh>\d{2}):(?P<mm>\d{2})(?:\+(?P<days>\d+))?$")


def resolve_dt(value: str | datetime, ref: datetime) -> datetime:
    """Resolve a time token or ISO string against the reference time."""
    if isinstance(value, datetime):
        return value
    text = str(value).strip()

    m = _NOW_RE.match(text)
    if m:
        out = ref
        if m.group("n"):
            n = int(m.group("n"))
            unit = {"d": "days", "h": "hours", "m": "minutes"}[m.group("unit")]
            delta = timedelta(**{unit: n})
            out = ref + delta if m.group("sign") == "+" else ref - delta
        return out

    m = _NEXT_RE.match(text)
    if m:
        local_ref = ref.astimezone()
        candidate = local_ref.replace(
            hour=int(m.group("hh")),
            minute=int(m.group("mm")),
            second=0,
            microsecond=0,
        )
        if candidate <= local_ref + timedelta(hours=1):
            candidate += timedelta(days=1)
        if m.group("days"):
            candidate += timedelta(days=int(m.group("days")))
        return candidate

    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ref.tzinfo)
    return parsed


def resolve_tree(node, ref: datetime):
    """Recursively resolve every time token in a nested structure."""
    if isinstance(node, dict):
        return {k: resolve_tree(v, ref) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve_tree(v, ref) for v in node]
    if isinstance(node, str) and (_NOW_RE.match(node) or _NEXT_RE.match(node)):
        return resolve_dt(node, ref)
    return node


def _deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_world(db: Session) -> dict:
    """Snapshot the seeded world into plain dicts the tools can query."""
    technicians: dict[str, dict] = {}
    for tech in db.query(Technician).all():
        technicians[tech.id] = {
            "id": tech.id,
            "name": tech.name,
            "lat": tech.lat,
            "lng": tech.lng,
            "working_start": tech.working_start,
            "working_end": tech.working_end,
            "skills": {s["skill"]: dict(s) for s in (tech.skills or [])},
            "inventory": {},
            "appointments": [],
        }
    for inv in db.query(TechnicianInventory).all():
        if inv.technician_id in technicians:
            technicians[inv.technician_id]["inventory"][inv.part_id] = inv.quantity
    for appt in db.query(Appointment).all():
        if appt.technician_id in technicians:
            technicians[appt.technician_id]["appointments"].append(
                {"start_at": appt.start_at, "duration_hours": appt.duration_hours}
            )
    return {
        "technicians": technicians,
        "sla_dispatch_hours": dict(SLA_DISPATCH_HOURS),
    }


def apply_overrides(world: dict, overrides: dict | None) -> dict:
    """Merge a scenario's world mutations into the snapshot.

    Supported shapes:
      {"technicians": {"<id>": {<merged fields>, "appointments_add": [...]}}}
      {"inventory": {"<tech_id>": {"<part_id>": <qty>}}}
    """
    if not overrides:
        return world

    for tech_id, patch in (overrides.get("technicians") or {}).items():
        tech = world["technicians"].get(tech_id)
        if tech is None:
            continue
        patch = dict(patch)
        extra_appts = patch.pop("appointments_add", None)
        world["technicians"][tech_id] = _deep_merge(tech, patch)
        if extra_appts:
            world["technicians"][tech_id]["appointments"] = (
                tech["appointments"] + list(extra_appts)
            )

    for tech_id, parts in (overrides.get("inventory") or {}).items():
        tech = world["technicians"].get(tech_id)
        if tech is not None:
            tech["inventory"] = {**tech["inventory"], **parts}

    return world


def build_world(db: Session, ref: datetime, overrides: dict | None = None) -> dict:
    """Load world, apply scenario overrides, resolve all time tokens."""
    world = load_world(db)
    world = apply_overrides(world, overrides)
    world = resolve_tree(world, ref)
    # Derive appointment end times from their durations after resolution.
    for tech in world["technicians"].values():
        for appt in tech["appointments"]:
            start = appt["start_at"]
            if isinstance(start, datetime):
                appt["end_at"] = start + timedelta(
                    hours=appt.get("duration_hours", 1.0)
                )
    return world
