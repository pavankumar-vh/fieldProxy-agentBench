"""Groq-powered dispatch agent (engine "groq").

Groq serves open models through an OpenAI-compatible API with generous
free-tier rate limits and very fast inference — the tool loop here speaks
that format (messages + tool_calls), while the decision contract, tools
and step trace stay identical to the other engines, so all versions are
graded on the same deterministic yardstick.
"""

import json
import time
from datetime import datetime

import httpx

from app.services.agent import DispatchAgent
from app.services.gemini import (
    MAX_RETRIES,
    RETRYABLE_STATUS,
    SYSTEM_PROMPT,
    TOOL_DECLARATIONS,
    VALID_ACTIONS,
    ProviderNotConfigured,
)

MAX_TOOL_ROUNDS = 8

# Smaller open models occasionally emit unparseable output; a corrective
# nudge round usually recovers without failing the case.
REPAIR_NUDGE = (
    "Your previous output could not be parsed. Respond ONLY by calling the "
    "submit_decision function — no prose, no markdown, no JSON in content."
)

# Official exit path: models sometimes try to emit their final answer via an
# invented tool (e.g. "json"), which Groq rejects. Giving them a declared
# submit_decision function makes the terminal step deterministic.
SUBMIT_DECISION_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_decision",
        "description": (
            "Submit your final dispatch decision. Call this exactly once when "
            "you have enough evidence from the other tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["assign", "reject", "defer", "escalate", "propose_slot"],
                },
                "technician_id": {"type": ["string", "null"]},
                "scheduled_at": {"type": ["string", "null"]},
                "reason": {"type": "string"},
            },
            "required": ["action", "reason"],
        },
    },
}

# Gemini-style declarations → OpenAI function-calling schema.
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        },
    }
    for t in TOOL_DECLARATIONS
] + [SUBMIT_DECISION_TOOL]


class GroqAgent(DispatchAgent):
    """Real LLM agent: OpenAI-compatible tool loop against Groq."""

    def __init__(
        self,
        world: dict,
        policy: dict,
        now: datetime,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ):
        # Empty policy: the LLM decides — no deterministic gates apply.
        super().__init__(world, {}, now)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ── helpers ───────────────────────────────────────────────────────
    def _assert_configured(self) -> None:
        if not self.api_key:
            raise ProviderNotConfigured(
                "GROQ_API_KEY is not set — add it to apps/api/.env to run "
                "the Groq agent for real (free keys: https://console.groq.com)"
            )

    def _intent_step(self, request: dict) -> dict:
        return self._record(
            "intent_parsing",
            "INTENT PARSING",
            lambda: {
                "intent": "schedule_job",
                "engine": "groq",
                "model": self.model,
                "job_type": request["job_type"],
                "urgency": request["urgency"],
                "requested_time": request["requested_at"].isoformat(),
            },
            {"raw_request": request.get("request_text", "")},
        )

    def _briefing(self, request: dict) -> str:
        def dt(o):
            return o.isoformat() if isinstance(o, datetime) else str(o)

        return (
            "World state (workforce snapshot):\n"
            + json.dumps(self.world["technicians"], indent=1, default=dt)
            + "\nSLA dispatch hours: "
            + json.dumps(self.world["sla_dispatch_hours"])
            + "\n\nJob request:\n"
            + json.dumps(
                {k: v for k, v in request.items() if k != "_now"},
                indent=1,
                default=dt,
            )
            + "\n\nUse the tools to verify facts. For your final answer call "
            "submit_decision — never print JSON or prose as the final answer."
        )

    def _call_groq(self, messages: list[dict]) -> dict:
        return self._post_chat(messages)

    def _post_chat(self, messages: list[dict], repaired: bool = False) -> dict:
        resp = None
        for attempt in range(MAX_RETRIES):
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": OPENAI_TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.0,
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            if resp.status_code not in RETRYABLE_STATUS:
                break
            if attempt < MAX_RETRIES - 1:
                wait = 15 * (attempt + 1) if resp.status_code == 429 else 2 * (attempt + 1)
                time.sleep(wait)
        if resp.status_code == 400 and not repaired:
            # Unparseable model output — one corrective retry.
            return self._post_chat(
                [*messages, {"role": "user", "content": REPAIR_NUDGE}],
                repaired=True,
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"Groq error {resp.status_code}: {resp.text[:400]}")
        return resp.json()

    def _exec_tool(self, name: str, args: dict) -> dict:
        def at(a: dict) -> datetime:
            return (
                datetime.fromisoformat(a["requested_at"])
                if a.get("requested_at")
                else self.now
            )

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
                a["technician_id"], at(a), a.get("duration_hours", 2)
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
    def run(self, request: dict) -> dict:
        self._assert_configured()
        intent = self._intent_step(request)
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._briefing(request)},
        ]

        decision: dict | None = None
        for _ in range(MAX_TOOL_ROUNDS):
            response = self._record(
                "llm_call",
                f"groq:{self.model}",
                lambda m=list(messages): self._call_groq(m),
                {"messages": len(messages)},
            )
            message = response["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                decision = self._parse_decision(message.get("content") or "")
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                fn = call["function"]
                args = json.loads(fn.get("arguments") or "{}")
                # The terminal tool: the decision arrives as structured args.
                if fn["name"] == "submit_decision":
                    if args.get("action") not in VALID_ACTIONS:
                        raise ValueError(f"invalid decision action: {args.get('action')!r}")
                    decision = {
                        "action": args["action"],
                        "technician_id": args.get("technician_id"),
                        "scheduled_at": args.get("scheduled_at"),
                        "reason": args.get("reason", ""),
                    }
                    break
                result = self._record(
                    "tool_call",
                    f"{fn['name']}()",
                    lambda n=fn["name"], a=args: self._exec_tool(n, a),
                    args,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, default=str),
                    }
                )
            if decision is not None:
                break

        if decision is None:
            raise RuntimeError(
                f"model did not produce a decision within {MAX_TOOL_ROUNDS} rounds"
            )
        return self._finalize(decision, intent, request)
