"""LLM-powered dispatch agent backed by the Gemini REST API.

This is a real tool-use loop: the model receives the job request plus the
six dispatch tools, calls them against the world snapshot, and finally emits
a JSON decision. No SDK, no mocks — plain https via httpx, so any
OpenAI-compatible/Gemini-style endpoint can be pointed at via
`gemini_base_url` (Google AI Studio, a proxy, or a local test server).

The decision contract is identical to `DispatchAgent.run()`, so the same
deterministic evaluator grades LLM and policy runs alike.
"""

import json
from datetime import datetime

import httpx

from app.services.agent import DispatchAgent


# Raised when an LLM-engine agent version is benchmarked without credentials.
# The runner turns this into a per-case "error" result — never a fake pass.
class ProviderNotConfigured(RuntimeError):
    pass


TOOL_DECLARATIONS = [
    {
        "name": "find_technician",
        "description": "Check whether a technician ID exists in the workforce.",
        "parameters": {
            "type": "object",
            "properties": {"technician_id": {"type": "string"}},
            "required": ["technician_id"],
        },
    },
    {
        "name": "find_available_technicians",
        "description": (
            "List technicians holding a skill, sorted by distance from the job."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "requested_at": {"type": "string", "description": "ISO datetime"},
                "location": {
                    "type": "object",
                    "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}},
                },
            },
            "required": ["skill"],
        },
    },
    {
        "name": "check_skills",
        "description": "Check a technician's certifications incl. expiry dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "technician_id": {"type": "string"},
                "required": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["technician_id", "required"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check whether a technician carries the required parts.",
        "parameters": {
            "type": "object",
            "properties": {
                "technician_id": {"type": "string"},
                "parts": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["technician_id", "parts"],
        },
    },
    {
        "name": "check_schedule",
        "description": (
            "Check whether a technician is free at the requested time; returns "
            "the next free slot if not."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "technician_id": {"type": "string"},
                "requested_at": {"type": "string", "description": "ISO datetime"},
                "duration_hours": {"type": "number"},
            },
            "required": ["technician_id", "requested_at"],
        },
    },
    {
        "name": "check_sla",
        "description": (
            "Check whether the requested time is inside the dispatch SLA window "
            "for the job's urgency."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "job_type": {"type": "string"},
                "urgency": {"type": "string"},
                "requested_at": {"type": "string", "description": "ISO datetime"},
            },
            "required": ["job_type", "urgency", "requested_at"],
        },
    },
]

SYSTEM_PROMPT = """You are a field-service dispatch agent. Given a repair job
request, decide what to do using ONLY the provided tools — never guess facts
about technicians, inventory, schedules or SLAs.

Rules you must follow:
- Never assign a technician whose required certification is expired.
- Never assign a technician who lacks a required part or has a schedule
  conflict at the requested time.
- If the requested time is outside the SLA dispatch window for that urgency,
  escalate instead of assigning.
- If a preferred technician ID does not exist, reject the request.
- If the request is outside working hours, propose the next slot.

When you have enough evidence, reply with ONLY a JSON object (no markdown,
no prose) of exactly this shape:
{"action": "assign"|"reject"|"defer"|"escalate"|"propose_slot",
 "technician_id": "<tech id or null>",
 "scheduled_at": "<ISO datetime or null>",
 "reason": "<one sentence>"}
"""

VALID_ACTIONS = {"assign", "reject", "defer", "escalate", "propose_slot"}
MAX_TOOL_ROUNDS = 8


class GeminiAgent(DispatchAgent):
    """Real LLM agent: Gemini function-calling loop over the same tools."""

    def __init__(
        self,
        world: dict,
        policy: dict,
        now: datetime,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 30.0,
    ):
        # Empty policy: the LLM decides — no deterministic gates apply.
        super().__init__(world, {}, now)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ── helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _json_default(o):
        return o.isoformat() if isinstance(o, datetime) else str(o)

    def _serializable_world(self) -> dict:
        return {
            "technicians": self.world["technicians"],
            "sla_dispatch_hours": self.world["sla_dispatch_hours"],
        }

    def _call_gemini(self, contents: list[dict]) -> dict:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": [{"function_declarations": TOOL_DECLARATIONS}],
            "generationConfig": {"temperature": 0.0},
        }
        resp = httpx.post(
            url,
            json=payload,
            headers={"x-goog-api-key": self.api_key},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _extract(response: dict) -> tuple[list[dict], str]:
        """Return (function_calls, text) from a Gemini response."""
        calls, text = [], ""
        for part in response.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "functionCall" in part:
                calls.append(part["functionCall"])
            elif "text" in part:
                text += part["text"]
        return calls, text

    def _exec_tool(self, name: str, args: dict) -> dict:
        # LLMs occasionally omit optional args — default sensibly.
        def at(a: dict) -> datetime:
            return datetime.fromisoformat(a["requested_at"]) if a.get("requested_at") else self.now

        handlers = {
            "find_technician": lambda a: self._tool_find_technician(a["technician_id"]),
            "find_available_technicians": lambda a: self._tool_find_available(
                a.get("skill", ""),
                at(a),
                a.get("location", {"lat": 12.9716, "lng": 77.5946}),
            ),
            "check_skills": lambda a: self._tool_check_skills(
                a["technician_id"], a.get("required", [])
            ),
            "check_inventory": lambda a: self._tool_check_inventory(
                a["technician_id"], a.get("parts", [])
            ),
            "check_schedule": lambda a: self._tool_check_schedule(
                a["technician_id"],
                at(a),
                a.get("duration_hours", 2),
            ),
            "check_sla": lambda a: self._tool_check_sla(
                a["job_type"], a["urgency"], at(a)
            ),
        }
        if name not in handlers:
            raise ValueError(f"unknown tool: {name}")
        return handlers[name](args)

    @staticmethod
    def _parse_decision(text: str) -> dict:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"model returned no JSON decision: {text[:200]!r}")
        decision = json.loads(text[start : end + 1])
        if decision.get("action") not in VALID_ACTIONS:
            raise ValueError(f"invalid decision action: {decision.get('action')!r}")
        return {
            "action": decision["action"],
            "technician_id": decision.get("technician_id"),
            "scheduled_at": decision.get("scheduled_at"),
            "reason": decision.get("reason", ""),
        }

    # ── main run ──────────────────────────────────────────────────────
    def _assert_configured(self) -> None:
        if not self.api_key:
            raise ProviderNotConfigured(
                "GEMINI_API_KEY is not set — add it to apps/api/.env to run "
                "the LLM agent for real (free keys: https://aistudio.google.com)"
            )

    def _intent_step(self, request: dict, engine: str) -> dict:
        return self._record(
            "intent_parsing",
            "INTENT PARSING",
            lambda: {
                "intent": "schedule_job",
                "engine": engine,
                "model": self.model,
                "job_type": request["job_type"],
                "urgency": request["urgency"],
                "requested_time": request["requested_at"].isoformat(),
            },
            {"raw_request": request.get("request_text", "")},
        )

    def _briefing(self, request: dict) -> str:
        return (
            "World state (workforce snapshot):\n"
            + json.dumps(self._serializable_world(), indent=1, default=self._json_default)
            + "\n\nJob request:\n"
            + json.dumps(
                {k: v for k, v in request.items() if k != "_now"},
                indent=1,
                default=self._json_default,
            )
            + "\n\nUse the tools to verify facts, then return the final JSON decision."
        )

    def run(self, request: dict) -> dict:
        self._assert_configured()
        intent = self._intent_step(request, engine="gemini")
        contents: list[dict] = [
            {"role": "user", "parts": [{"text": self._briefing(request)}]}
        ]

        decision: dict | None = None
        for _ in range(MAX_TOOL_ROUNDS):
            response = self._record(
                "llm_call",
                f"gemini:{self.model}",
                lambda c=list(contents): self._call_gemini(c),
                {"messages": len(contents)},
            )
            calls, text = self._extract(response)

            if not calls:
                decision = self._parse_decision(text)
                break

            # Execute every requested tool against the real world snapshot.
            contents.append(response["candidates"][0]["content"])
            tool_parts = []
            for call in calls:
                args = call.get("args", {})
                result = self._record(
                    "tool_call",
                    f"{call['name']}()",
                    lambda n=call["name"], a=args: self._exec_tool(n, a),
                    args,
                )
                tool_parts.append(
                    {
                        "functionResponse": {
                            "name": call["name"],
                            "response": {"result": result},
                        }
                    }
                )
            contents.append({"role": "user", "parts": tool_parts})

        if decision is None:
            raise RuntimeError(
                f"model did not produce a decision within {MAX_TOOL_ROUNDS} rounds"
            )
        return self._finalize(decision, intent, request)
