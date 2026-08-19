"""LangGraph-powered dispatch agent — Phase 3 complete.

The same Gemini tool loop as `GeminiAgent`, but expressed as an explicit
LangGraph state machine:

    ┌───────────┐  tool_call   ┌───────────┐
    │   model   │ ───────────→ │   tools   │
    │  (Gemini) │ ←─────────── │  (world)  │
    └───────────┘   result     └───────────┘
          │ final JSON
          ▼
         END → deterministic evaluator grades it like any other engine

Reuses the parent's real HTTP calls, tool executors, decision parser and
step recording, so traces are comparable across engines.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.services.gemini import GeminiAgent


class _State(TypedDict, total=False):
    contents: list
    calls: list
    decision: dict | None


class LangGraphAgent(GeminiAgent):
    """Real LLM agent driven by a compiled LangGraph graph."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        graph = StateGraph(_State)
        graph.add_node("model", self._model_node)
        graph.add_node("tools", self._tools_node)
        graph.set_entry_point("model")
        graph.add_conditional_edges("model", self._route, {"tools": "tools", END: END})
        graph.add_edge("tools", "model")
        self._graph = graph.compile()

    # ── nodes ─────────────────────────────────────────────────────────
    def _model_node(self, state: _State) -> _State:
        response = self._record(
            "llm_call",
            f"gemini:{self.model}",
            lambda c=list(state["contents"]): self._call_gemini(c),
            {"messages": len(state["contents"]), "graph_node": "model"},
        )
        calls, text = self._extract(response)

        if not calls:
            return {"contents": state["contents"], "calls": [],
                    "decision": self._parse_decision(text)}

        return {
            "contents": [*state["contents"], response["candidates"][0]["content"]],
            "calls": calls,
            "decision": None,
        }

    def _tools_node(self, state: _State) -> _State:
        parts = []
        for call in state["calls"]:
            args = call.get("args", {})
            result = self._record(
                "tool_call",
                f"{call['name']}()",
                lambda n=call["name"], a=args: self._exec_tool(n, a),
                {**args, "graph_node": "tools"},
            )
            parts.append(
                {
                    "functionResponse": {
                        "name": call["name"],
                        "response": {"result": result},
                    }
                }
            )
        return {
            "contents": [*state["contents"], {"role": "user", "parts": parts}],
            "calls": [],
        }

    @staticmethod
    def _route(state: _State) -> str:
        return "tools" if state.get("calls") else END

    # ── main run ──────────────────────────────────────────────────────
    def run(self, request: dict) -> dict:
        self._assert_configured()
        intent = self._intent_step(request, engine="langgraph")
        initial: _State = {
            "contents": [{"role": "user", "parts": [{"text": self._briefing(request)}]}],
            "calls": [],
            "decision": None,
        }
        final = self._graph.invoke(initial)
        if not final.get("decision"):
            raise RuntimeError("graph finished without a decision")
        return self._finalize(final["decision"], intent, request)
