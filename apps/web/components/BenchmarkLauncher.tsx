"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAgents, startBenchmark } from "@/lib/api";
import type { AgentVersion } from "@/lib/types";

const BENCHMARKS = [
  { id: "full", label: "Full Benchmark (all cases)" },
  { id: "dispatch", label: "Dispatch Only" },
  { id: "critical", label: "Critical Cases Only" },
  { id: "mutations", label: "Mutation Tests Only" },
];

export default function BenchmarkLauncher() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentVersion[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentId, setAgentId] = useState("");
  const [benchmark, setBenchmark] = useState("full");
  const [mutations, setMutations] = useState(true);
  const [compareAgainst, setCompareAgainst] = useState("none");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedAgent = agents.find((a) => a.id === agentId);

  // Never offer the selected agent's own version as a baseline.
  const compareVersions = [
    "none",
    ...Array.from(new Set(agents.map((a) => a.version))).filter(
      (v) => v !== selectedAgent?.version
    ),
  ];

  useEffect(() => {
    getAgents()
      .then((list) => {
        setAgents(list);
        const active = list.find((a) => a.status === "active");
        const selected = active ?? list[0];
        setAgentId(selected?.id ?? "");
        // Default the comparison to the newest *different* version, if one exists.
        const other = list.find((a) => a.version !== selected?.version);
        setCompareAgainst(other?.version ?? "none");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load agents"))
      .finally(() => setAgentsLoading(false));
  }, []);

  // If the agent changed and the current comparison is now its own version,
  // fall back to "none" instead of comparing the version against itself.
  useEffect(() => {
    if (selectedAgent && compareAgainst === selectedAgent.version) {
      setCompareAgainst("none");
    }
  }, [agentId, agents, compareAgainst, selectedAgent]);

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
            fontFamily: "var(--font-space-mono), monospace",
            fontSize: "0.7rem",
            background: "var(--black)",
            color: "var(--yellow)",
            padding: "0.2rem 0.5rem",
            letterSpacing: "0.1em",
          }}
        >
          01
        </span>
        <h2 style={{ fontSize: "1rem", fontFamily: "var(--font-space-mono), monospace", letterSpacing: "0.1em" }}>
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
          <label className="label-field" htmlFor="agent-select">AGENT</label>
          <select
            id="agent-select"
            className="select-brutal"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          >
            {agentsLoading && <option value="">LOADING…</option>}
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} {a.version} ({a.status})
              </option>
            ))}
          </select>
        </div>

        {/* Benchmark */}
        <div>
          <label className="label-field" htmlFor="benchmark-select">BENCHMARK</label>
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
          <label className="label-field" htmlFor="compare-select">COMPARE AGAINST</label>
          <select
            id="compare-select"
            className="select-brutal"
            value={compareAgainst}
            onChange={(e) => setCompareAgainst(e.target.value)}
          >
            {compareVersions.map((v) => (
              <option key={v} value={v}>{v === "none" ? "No comparison" : v}</option>
            ))}
          </select>
        </div>

        {/* Mutation toggle */}
        <div>
          <label className="label-field" htmlFor="mutation-toggle">MUTATION TESTING</label>
          <button
            type="button"
            id="mutation-toggle"
            className="toggle-wrap"
            style={{ marginTop: "0.6rem" }}
            aria-pressed={mutations}
            onClick={() => setMutations((m) => !m)}
          >
            <span className={`toggle-track ${mutations ? "on" : ""}`}>
              <span className="toggle-thumb" />
            </span>
            <span
              style={{
                fontFamily: "var(--font-space-mono), monospace",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              {mutations ? "ON" : "OFF"}
            </span>
          </button>
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
            fontFamily: "var(--font-space-mono), monospace",
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
        disabled={loading || agentsLoading || !agentId}
        style={{
          opacity: loading || agentsLoading || !agentId ? 0.6 : 1,
          cursor: loading || agentsLoading || !agentId ? "not-allowed" : "pointer",
        }}
      >
        {loading
          ? "⏳ LAUNCHING..."
          : agentsLoading
          ? "⏳ LOADING AGENTS..."
          : "▶ RUN TESTS"}
      </button>

      <p
        style={{
          marginTop: "1rem",
          fontFamily: "var(--font-space-mono), monospace",
          fontSize: "0.7rem",
          color: "var(--gray-700)",
        }}
      >
        Executes the selected agent against the seeded field-service world.
        Every result is computed live and persisted — nothing is simulated.
      </p>
    </div>
  );
}
