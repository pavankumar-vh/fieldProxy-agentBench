"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startBenchmark } from "@/lib/api";

const AGENTS = [
  { id: "av_001", label: "Dispatch Agent v1.2 (active)" },
  { id: "av_002", label: "Dispatch Agent v1.1 (deprecated)" },
  { id: "av_003", label: "Dispatch Agent v1.0 (deprecated)" },
];

const BENCHMARKS = [
  { id: "full", label: "Full Benchmark (30 cases)" },
  { id: "dispatch", label: "Dispatch Only (7 cases)" },
  { id: "critical", label: "Critical Cases Only" },
  { id: "mutations", label: "Mutation Tests Only" },
];

const VERSIONS = ["none", "v1.0", "v1.1", "v1.2"];

export default function BenchmarkLauncher() {
  const router = useRouter();
  const [agentId, setAgentId] = useState("av_001");
  const [benchmark, setBenchmark] = useState("full");
  const [mutations, setMutations] = useState(true);
  const [compareAgainst, setCompareAgainst] = useState("v1.1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const { run_id } = await startBenchmark({
        agent_version_id: agentId,
        benchmark_type: benchmark,
        mutation_testing: mutations,
        compare_against: compareAgainst === "none" ? undefined : compareAgainst,
      });
      router.push(`/runs/${run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start benchmark");
      setLoading(false);
    }
  }

  return (
    <div
      className="card-yellow"
      style={{ padding: "2rem", marginBottom: "1rem", boxShadow: "8px 8px 0 var(--black)" }}
    >
      <div className="section-header" style={{ marginBottom: "1.5rem", borderColor: "var(--black)" }}>
        <span
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: "0.7rem",
            background: "var(--black)",
            color: "var(--yellow)",
            padding: "0.2rem 0.5rem",
            letterSpacing: "0.1em",
          }}
        >
          01
        </span>
        <h2 style={{ fontSize: "1rem", fontFamily: "'Space Mono',monospace", letterSpacing: "0.1em" }}>
          LAUNCH BENCHMARK
        </h2>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        {/* Agent */}
        <div>
          <label className="label-field">AGENT</label>
          <select
            id="agent-select"
            className="select-brutal"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          >
            {AGENTS.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
        </div>

        {/* Benchmark */}
        <div>
          <label className="label-field">BENCHMARK</label>
          <select
            id="benchmark-select"
            className="select-brutal"
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
          >
            {BENCHMARKS.map((b) => (
              <option key={b.id} value={b.id}>{b.label}</option>
            ))}
          </select>
        </div>

        {/* Compare Against */}
        <div>
          <label className="label-field">COMPARE AGAINST</label>
          <select
            id="compare-select"
            className="select-brutal"
            value={compareAgainst}
            onChange={(e) => setCompareAgainst(e.target.value)}
          >
            {VERSIONS.map((v) => (
              <option key={v} value={v}>{v === "none" ? "No comparison" : v}</option>
            ))}
          </select>
        </div>

        {/* Mutation toggle */}
        <div>
          <label className="label-field">MUTATION TESTING</label>
          <div
            className="toggle-wrap"
            style={{ marginTop: "0.6rem" }}
            onClick={() => setMutations((m) => !m)}
          >
            <div className={`toggle-track ${mutations ? "on" : ""}`}>
              <div className="toggle-thumb" />
            </div>
            <span
              style={{
                fontFamily: "'Space Mono', monospace",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              {mutations ? "ON" : "OFF"}
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: "var(--red)",
            color: "var(--white)",
            border: "2px solid var(--black)",
            padding: "0.75rem 1rem",
            marginBottom: "1rem",
            fontFamily: "'Space Mono', monospace",
            fontSize: "0.8rem",
          }}
        >
          ✗ BENCHMARK EXECUTION FAILED: {error}
        </div>
      )}

      <button
        id="run-benchmark-btn"
        className="btn btn-black btn-xl"
        onClick={handleRun}
        disabled={loading}
        style={{ opacity: loading ? 0.6 : 1, cursor: loading ? "not-allowed" : "pointer" }}
      >
        {loading ? "⏳ LAUNCHING..." : "▶ RUN TESTS"}
      </button>

      <p
        style={{
          marginTop: "1rem",
          fontFamily: "'Space Mono', monospace",
          fontSize: "0.7rem",
          color: "var(--gray-700)",
        }}
      >
        ⚠ Phase 1: Redirects to fixture run. Phase 2: Triggers real FastAPI benchmark execution.
      </p>
    </div>
  );
}
