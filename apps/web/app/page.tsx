import { getDashboardMetrics, getRuns } from "@/lib/api";
import Link from "next/link";
import { formatPercent, formatDateTime, formatDuration } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [metrics, runs] = await Promise.all([
    getDashboardMetrics(),
    getRuns(),
  ]);

  const recentRuns = runs.slice(0, 5);

  const tickerItems = [
    `DISPATCH AGENT v1.2 — PASS RATE ${formatPercent(metrics.agent_reliability)}`,
    `TOTAL RUNS: ${metrics.total_runs}`,
    `TEST CASES: ${metrics.total_test_cases}`,
    `CRITICAL FAILURES: ${metrics.critical}`,
    `LAST RUN: ${metrics.last_run_at ? formatDateTime(metrics.last_run_at) : "NEVER"}`,
    `ACTIVE AGENTS: ${metrics.active_agents}`,
  ];

  return (
    <>
      {/* Ticker */}
      <div className="ticker-bar">
        <div className="ticker-inner">
          {[...tickerItems, ...tickerItems].map((item, i) => (
            <span key={i}>◆ {item}</span>
          ))}
        </div>
      </div>

      <div className="page">
        {/* Hero */}
        <div
          style={{
            padding: "3rem 0 2rem",
            borderBottom: "3px solid var(--black)",
            marginBottom: "2rem",
          }}
        >
          <p
            className="label-mono"
            style={{ color: "var(--gray-500)", marginBottom: "0.75rem" }}
          >
            ▶ FIELDPROXY — INDEPENDENT PROTOTYPE
          </p>
          <h1 className="display-xl" style={{ marginBottom: "0.5rem" }}>
            FIELDPROXY
            <br />
            <span style={{ color: "var(--blue)" }}>AGENTBENCH</span>
          </h1>
          <p
            className="display-md"
            style={{
              color: "var(--gray-500)",
              fontWeight: 400,
              fontSize: "1.1rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "1.5rem",
            }}
          >
            REGRESSION TESTING FOR FIELD-SERVICE AI
          </p>
          <p
            style={{
              maxWidth: "560px",
              fontSize: "1rem",
              color: "var(--gray-700)",
              lineHeight: 1.6,
              marginBottom: "2rem",
            }}
          >
            An independent prototype built specifically around Fieldproxy&apos;s
            publicly documented AI/FSM workflows. Tests, evaluates, and tracks
            AI agent reliability end-to-end.
          </p>

          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <Link href="/runs" className="btn btn-yellow btn-xl">
              ▶ RUN BENCHMARK
            </Link>
            <Link href="/agents" className="btn btn-black btn-xl">
              VIEW AGENTS
            </Link>
            <Link href="/regressions" className="btn btn-cream btn-xl">
              REGRESSIONS
            </Link>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid-4" style={{ marginBottom: "2.5rem" }}>
          <div
            className="stat-card"
            style={{ background: "var(--black)", color: "var(--cream)", boxShadow: "6px 6px 0 var(--yellow)" }}
          >
            <span className="stat-card-label" style={{ color: "var(--gray-300)" }}>
              AGENT RELIABILITY
            </span>
            <span
              className="stat-card-value"
              style={{ color: "var(--yellow)", fontSize: "3.5rem" }}
            >
              {formatPercent(metrics.agent_reliability)}
            </span>
            <span className="stat-card-sub" style={{ color: "var(--gray-300)" }}>
              Dispatch Agent v1.2
            </span>
          </div>

          <div className="stat-card">
            <span className="stat-card-label">TEST CASES</span>
            <span className="stat-card-value">{metrics.total_test_cases}</span>
            <span className="stat-card-sub">Across all categories</span>
          </div>

          <div
            className="stat-card"
            style={{ background: "var(--green)", boxShadow: "6px 6px 0 var(--black)" }}
          >
            <span className="stat-card-label">PASSED</span>
            <span className="stat-card-value">{metrics.passed}</span>
            <span className="stat-card-sub">Last benchmark run</span>
          </div>

          <div
            className="stat-card"
            style={{ background: "var(--red)", color: "var(--white)", boxShadow: "6px 6px 0 var(--black)" }}
          >
            <span className="stat-card-label" style={{ color: "rgba(255,255,255,0.7)" }}>
              FAILED
            </span>
            <span className="stat-card-value">{metrics.failed}</span>
            <span className="stat-card-sub" style={{ color: "rgba(255,255,255,0.7)" }}>
              {metrics.critical} CRITICAL
            </span>
          </div>
        </div>

        {/* Second row metrics */}
        <div className="grid-3" style={{ marginBottom: "2.5rem" }}>
          <div className="stat-card" style={{ background: "var(--yellow)" }}>
            <span className="stat-card-label">ACTIVE AGENTS</span>
            <span className="stat-card-value">{metrics.active_agents}</span>
            <span className="stat-card-sub">Dispatch Agent family</span>
          </div>
          <div className="stat-card">
            <span className="stat-card-label">TOTAL RUNS</span>
            <span className="stat-card-value">{metrics.total_runs}</span>
            <span className="stat-card-sub">All time benchmark executions</span>
          </div>
          <div className="stat-card" style={{ background: "var(--blue)", color: "var(--white)" }}>
            <span className="stat-card-label" style={{ color: "rgba(255,255,255,0.7)" }}>
              LAST RUN
            </span>
            <span
              className="stat-card-value"
              style={{ fontSize: "1.5rem", color: "var(--white)" }}
            >
              {metrics.last_run_at
                ? formatDateTime(metrics.last_run_at)
                : "NEVER"}
            </span>
            <span className="stat-card-sub" style={{ color: "rgba(255,255,255,0.7)" }}>
              Dispatch Agent v1.2
            </span>
          </div>
        </div>

        {/* Architecture Diagram */}
        <div style={{ marginBottom: "2.5rem" }}>
          <div className="section-header">
            <span className="section-num">01</span>
            <h2 style={{ fontSize: "1rem", fontFamily: "'Space Mono',monospace", letterSpacing: "0.1em" }}>
              EXECUTION PIPELINE
            </h2>
          </div>
          <div
            className="card"
            style={{
              background: "var(--black)",
              color: "var(--cream)",
              padding: "2rem",
              fontFamily: "'Space Mono', monospace",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0",
                flexWrap: "wrap",
                fontSize: "0.75rem",
                letterSpacing: "0.05em",
              }}
            >
              {[
                { label: "NEXT.JS", color: "var(--yellow)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "FASTAPI", color: "var(--blue-light)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "POSTGRESQL", color: "var(--green)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "LANGGRAPH", color: "var(--pink)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "GEMINI", color: "var(--yellow)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "REAL TOOLS", color: "var(--blue-light)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "EVALUATOR", color: "var(--green)" },
                { label: "→", color: "var(--gray-500)" },
                { label: "RESULTS", color: "var(--yellow)" },
              ].map((item, i) => (
                <span key={i} style={{ color: item.color, padding: "0 0.4rem" }}>
                  {item.label}
                </span>
              ))}
            </div>
            <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              {[
                { label: "LangGraph", status: "Phase 3" },
                { label: "Gemini API", status: "Phase 3" },
                { label: "PostgreSQL", status: "Phase 2" },
                { label: "FastAPI", status: "Phase 2" },
                { label: "Frontend", status: "✓ Active" },
                { label: "Evaluator", status: "Phase 4" },
              ].map(({ label, status }) => (
                <div
                  key={label}
                  style={{
                    border: "1.5px solid var(--gray-700)",
                    padding: "0.4rem 0.75rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.2rem",
                  }}
                >
                  <span style={{ fontSize: "0.65rem", color: "var(--gray-500)", letterSpacing: "0.08em" }}>
                    {label}
                  </span>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      color: status.startsWith("✓") ? "var(--green)" : "var(--gray-300)",
                    }}
                  >
                    {status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Runs */}
        <div>
          <div className="section-header">
            <span className="section-num">02</span>
            <h2 style={{ fontSize: "1rem", fontFamily: "'Space Mono',monospace", letterSpacing: "0.1em" }}>
              RECENT BENCHMARK RUNS
            </h2>
            <Link
              href="/runs"
              className="btn btn-black btn-sm"
              style={{ marginLeft: "auto" }}
            >
              VIEW ALL →
            </Link>
          </div>

          <div
            style={{
              border: "3px solid var(--black)",
              boxShadow: "var(--shadow)",
              overflow: "hidden",
            }}
          >
            <table className="table-brutal">
              <thead>
                <tr>
                  <th>RUN ID</th>
                  <th>AGENT</th>
                  <th>VERSION</th>
                  <th>STATUS</th>
                  <th>PASS RATE</th>
                  <th>TESTS</th>
                  <th>FAILED</th>
                  <th>DURATION</th>
                  <th>STARTED</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <span
                        className="font-mono"
                        style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}
                      >
                        {run.id}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{run.agent_name}</td>
                    <td>
                      <span className="badge badge-black">{run.agent_version}</span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          run.status === "completed"
                            ? "badge-pass"
                            : run.status === "running"
                            ? "badge-info"
                            : "badge-fail"
                        }`}
                      >
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontFamily: "'Space Mono', monospace",
                          fontWeight: 700,
                          color:
                            run.pass_rate >= 95
                              ? "var(--green-dark)"
                              : run.pass_rate >= 80
                              ? "var(--orange)"
                              : "var(--red)",
                        }}
                      >
                        {formatPercent(run.pass_rate)}
                      </span>
                    </td>
                    <td className="font-mono">{run.total_tests}</td>
                    <td>
                      {run.failed > 0 ? (
                        <span style={{ color: "var(--red)", fontWeight: 700, fontFamily: "monospace" }}>
                          {run.failed}
                        </span>
                      ) : (
                        <span style={{ color: "var(--green-dark)", fontFamily: "monospace" }}>0</span>
                      )}
                    </td>
                    <td className="font-mono" style={{ color: "var(--gray-500)" }}>
                      {formatDuration(run.duration_ms)}
                    </td>
                    <td style={{ color: "var(--gray-500)", fontSize: "0.8rem" }}>
                      {formatDateTime(run.started_at)}
                    </td>
                    <td>
                      <Link
                        href={`/runs/${run.id}`}
                        className="btn btn-black btn-sm"
                      >
                        VIEW →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
