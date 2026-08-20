"""End-to-end API tests over SQLite — real execution, no mocks."""


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_agents_listed_with_derived_stats(client):
    res = client.get("/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) == 6
    by_id = {a["id"]: a for a in agents}
    assert by_id["av_001"]["status"] == "active"
    assert by_id["av_004"]["engine"] == "gemini"
    assert by_id["av_005"]["engine"] == "langgraph"
    assert by_id["av_006"]["engine"] == "groq"
    # No runs yet for this version in a fresh test DB → zeroed stats.
    assert "pass_rate" in by_id["av_001"]


def test_test_cases_listed(client):
    res = client.get("/test-cases")
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) == 13
    mutations = [c for c in cases if c["is_mutation"]]
    assert len(mutations) == 3


def test_full_benchmark_execution_strict_version(client):
    res = client.post(
        "/benchmark/run",
        json={
            "agent_version_id": "av_002",
            "benchmark_type": "full",
            "mutation_testing": True,
        },
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "completed"
    assert detail["total_tests"] == 13
    # The strict policy passes the whole suite.
    assert detail["passed"] == 13
    assert detail["pass_rate"] == 100.0
    # Real trace data for the featured case.
    assert detail["agent_request"]
    assert len(detail["steps"]) > 0
    assert detail["steps"][0]["type"] == "intent_parsing"
    assert len(detail["evaluation"]) > 0
    assert detail["latency_ms"] >= 1


def test_buggy_version_regresses_against_baseline(client):
    res = client.post(
        "/benchmark/run",
        json={
            "agent_version_id": "av_001",
            "benchmark_type": "full",
            "mutation_testing": True,
            "compare_against": "v1.1",
        },
    )
    assert res.status_code == 201
    run_id = res.json()["run_id"]
    detail = client.get(f"/runs/{run_id}").json()
    assert detail["failed"] > 0
    assert detail["critical_failures"] > 0

    reports = client.get("/regressions").json()
    assert len(reports) >= 1
    latest = reports[0]
    assert latest["current_version"] == "v1.2"
    assert latest["baseline_version"] == "v1.1"
    assert latest["regression_detected"] is True
    assert latest["delta"] < 0
    assert len(latest["new_failures"]) > 0
    # new_failures are full TestCase objects for the frontend table.
    assert "scenario" in latest["new_failures"][0]


def test_agent_metrics_derived_from_runs(client):
    res = client.get("/agents/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["total_test_cases"] == 13
    assert metrics["total_runs"] >= 2
    assert metrics["last_run_at"] is not None
    assert metrics["active_agents"] == 1


def test_unknown_run_404(client):
    assert client.get("/runs/run_nope").status_code == 404


def test_run_can_be_deleted(client):
    res = client.post(
        "/benchmark/run",
        json={"agent_version_id": "av_002", "benchmark_type": "critical"},
    )
    run_id = res.json()["run_id"]
    assert client.delete(f"/runs/{run_id}").status_code == 204
    assert client.get(f"/runs/{run_id}").status_code == 404
    assert client.delete(f"/runs/{run_id}").status_code == 404


def test_concurrent_benchmark_rejected(client):
    """Only one benchmark may run at a time (free-tier LLM quota)."""
    from app.database import SessionLocal
    from app.models import BenchmarkRun

    db = SessionLocal()
    blocker = BenchmarkRun(
        id="run_blocker",
        agent_version_id="av_002",
        status="running",
        benchmark_type="full",
        triggered_by="test",
    )
    db.add(blocker)
    db.commit()
    db.close()
    try:
        res = client.post("/benchmark/run", json={"agent_version_id": "av_002"})
        assert res.status_code == 409
        assert "already running" in res.json()["detail"]
    finally:
        db = SessionLocal()
        db.delete(db.get(BenchmarkRun, "run_blocker"))
        db.commit()
        db.close()


def test_invalid_benchmark_type_rejected(client):
    res = client.post(
        "/benchmark/run",
        json={"agent_version_id": "av_001", "benchmark_type": "bogus"},
    )
    assert res.status_code == 422


def test_self_comparison_rejected(client):
    """A version cannot regress against itself."""
    res = client.post(
        "/benchmark/run",
        json={"agent_version_id": "av_001", "compare_against": "v1.2"},
    )
    assert res.status_code == 422
