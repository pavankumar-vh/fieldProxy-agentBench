"""Groq agent tests.

Same discipline as the Gemini tests: the tool loop runs over REAL HTTP
against a local scripted OpenAI-compatible endpoint — the agent's message
building, tool dispatch and parsing execute for real; only the "model" is
scripted, as it must be without network credentials.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from test_gemini import _case_inputs

from app.services.groq import GroqAgent, ProviderNotConfigured


def test_missing_api_key_raises_honest_error():
    world, request, ref = _case_inputs("tc_001")
    agent = GroqAgent(
        world, {}, ref, api_key="", base_url="http://unused", model="m"
    )
    try:
        agent.run(request)
        raise AssertionError("expected ProviderNotConfigured")
    except ProviderNotConfigured as exc:
        assert "GROQ_API_KEY" in str(exc)


def _scripted_groq_server():
    """One tool_call round, then a final JSON decision (OpenAI format)."""
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body)
            if len(calls) == 1:
                message = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "find_available_technicians",
                                "arguments": json.dumps({"skill": "HVAC"}),
                            },
                        }
                    ],
                }
            else:
                # The model must have received the real tool result by now.
                assert any(m.get("role") == "tool" for m in body["messages"])
                message = {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "action": "assign",
                            "technician_id": "tech_007",
                            "scheduled_at": None,
                            "reason": "Nearest certified HVAC tech.",
                        }
                    ),
                }
            response = {"choices": [{"message": message}]}
            payload = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, calls


def test_tool_loop_over_real_http_openai_format():
    server, calls = _scripted_groq_server()
    try:
        world, request, ref = _case_inputs("tc_001")
        agent = GroqAgent(
            world,
            {},
            ref,
            api_key="test-key",
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            model="openai/gpt-oss-120b",
        )
        decision = agent.run(request)
    finally:
        server.shutdown()

    assert decision["action"] == "assign"
    assert decision["technician_id"] == "tech_007"
    # Two real HTTP round-trips, OpenAI-format tool schema on the wire.
    assert len(calls) == 2
    assert calls[0]["tools"][0]["type"] == "function"
    assert calls[1]["messages"][-1]["role"] == "tool"
    # Trace shape matches every other engine.
    types = [s["type"] for s in agent.steps]
    assert types[0] == "intent_parsing"
    assert "llm_call" in types and "tool_call" in types and types[-1] == "decision"
