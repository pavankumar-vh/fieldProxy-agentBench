"""Gemini agent tests.

The tool loop is exercised over REAL HTTP against a local scripted endpoint
(http.server in a thread) — the agent's parsing, tool dispatch and step
recording all execute for real; only the "model" is scripted, as it must be
without network credentials.
"""

import json
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.database import SessionLocal
from app.models import AgentVersion, TestCase
from app.services.gemini import GeminiAgent, ProviderNotConfigured
from app.services.world import build_world, resolve_tree


def _case_inputs(case_id: str):
    db = SessionLocal()
    try:
        tc = db.get(TestCase, case_id)
        ref = datetime.now(UTC)
        world = build_world(db, ref, tc.spec.get("world_overrides"))
        request = resolve_tree(dict(tc.spec["request"]), ref)
        request["_now"] = ref
        request.setdefault("request_text", tc.scenario)
        return world, request, ref
    finally:
        db.close()


def test_missing_api_key_raises_honest_error():
    world, request, ref = _case_inputs("tc_001")
    agent = GeminiAgent(
        world, {}, ref, api_key="", base_url="http://unused", model="gemini-2.0-flash"
    )
    try:
        agent.run(request)
        raise AssertionError("expected ProviderNotConfigured")
    except ProviderNotConfigured as exc:
        assert "GEMINI_API_KEY" in str(exc)


def test_benchmark_of_llm_version_without_key_records_errors(client):
    res = client.post(
        "/benchmark/run",
        json={"agent_version_id": "av_004", "benchmark_type": "critical"},
    )
    assert res.status_code == 201
    detail = client.get(f"/runs/{res.json()['run_id']}").json()
    # No fabricated passes: every case is an honest error.
    assert detail["status"] == "completed"
    assert detail["passed"] == 0
    assert detail["failed"] == detail["total_tests"]
    assert "GEMINI_API_KEY" in detail["error"]


def _scripted_gemini_server():
    """One function-call round, then a final JSON decision."""
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body)
            if len(calls) == 1:
                response = {
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "find_available_technicians",
                                            "args": {"skill": "HVAC"},
                                        }
                                    }
                                ],
                            }
                        }
                    ]
                }
            else:
                # The model must have received the real tool result by now.
                assert "functionResponse" in json.dumps(body)
                response = {
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "action": "assign",
                                                "technician_id": "tech_007",
                                                "scheduled_at": None,
                                                "reason": "Nearest certified HVAC tech.",
                                            }
                                        )
                                    }
                                ],
                            }
                        }
                    ]
                }
            payload = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, calls


def test_tool_loop_over_real_http():
    server, calls = _scripted_gemini_server()
    try:
        world, request, ref = _case_inputs("tc_001")
        agent = GeminiAgent(
            world,
            {},
            ref,
            api_key="test-key",
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            model="gemini-2.0-flash",
        )
        decision = agent.run(request)
    finally:
        server.shutdown()

    assert decision["action"] == "assign"
    assert decision["technician_id"] == "tech_007"
    # Two real HTTP round-trips happened…
    assert len(calls) == 2
    assert calls[0]["tools"][0]["function_declarations"][0]["name"] == "find_technician"
    # …and the trace recorded llm_call + tool_call steps with latencies.
    types = [s["type"] for s in agent.steps]
    assert types[0] == "intent_parsing"
    assert "llm_call" in types and "tool_call" in types and types[-1] == "decision"
    assert all(s["latency_ms"] >= 1 for s in agent.steps)


def test_invalid_decision_json_raises():
    world, _request, ref = _case_inputs("tc_001")
    agent = GeminiAgent(
        world, {}, ref, api_key="k", base_url="http://unused", model="m"
    )
    try:
        agent._parse_decision("no json here at all")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        agent._parse_decision('{"action": "teleport"}')
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_langgraph_state_machine_over_real_http():
    """The LangGraph engine must traverse model → tools → model for real."""
    from app.services.langgraph_agent import LangGraphAgent

    server, calls = _scripted_gemini_server()
    try:
        world, request, ref = _case_inputs("tc_001")
        agent = LangGraphAgent(
            world,
            {},
            ref,
            api_key="test-key",
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            model="gemini-2.0-flash",
        )
        decision = agent.run(request)
    finally:
        server.shutdown()

    assert decision["action"] == "assign"
    assert decision["technician_id"] == "tech_007"
    assert len(calls) == 2  # graph made two real Gemini round-trips
    # Trace shows the graph path: intent → llm_call → tool_call → llm_call → decision.
    types = [s["type"] for s in agent.steps]
    assert types[0] == "intent_parsing"
    assert types.count("llm_call") == 2
    assert "tool_call" in types and types[-1] == "decision"
    # The tool step was executed inside the "tools" graph node.
    tool_step = next(s for s in agent.steps if s["type"] == "tool_call")
    assert tool_step["input"]["graph_node"] == "tools"


def test_langgraph_version_without_key_records_errors(client):
    res = client.post(
        "/benchmark/run",
        json={"agent_version_id": "av_005", "benchmark_type": "critical"},
    )
    assert res.status_code == 201
    detail = client.get(f"/runs/{res.json()['run_id']}").json()
    assert detail["passed"] == 0
    assert "GEMINI_API_KEY" in detail["error"]


def test_sync_models_repairs_stale_llm_model_ids():
    """Google retires model IDs; boot-time sync must repair them."""
    from app.config import get_settings
    from scripts import sync_models

    db = SessionLocal()
    try:
        av = db.get(AgentVersion, "av_004")
        av.model = "gemini-0.0-retired"
        # Sentinel on a policy version: the sync must NOT touch it.
        policy_av = db.get(AgentVersion, "av_001")
        policy_av.model = "policy-engine"
        db.commit()
    finally:
        db.close()

    sync_models.main()

    db = SessionLocal()
    try:
        av = db.get(AgentVersion, "av_004")
        assert av.model == get_settings().gemini_model
        policy_av = db.get(AgentVersion, "av_001")
        assert policy_av.model == "policy-engine"
    finally:
        db.close()
