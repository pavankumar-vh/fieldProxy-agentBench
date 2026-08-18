import { getRegressions } from "@/lib/api";
import { formatPercent, formatDateTime } from "@/lib/utils";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Regressions — Fieldproxy AgentBench",
  description: "Detect and analyze regressions between agent versions. Compare pass rates, new failures, and critical changes.",
};

export const dynamic = "force-dynamic";

export default async function RegressionsPage() {
  const reports = await getRegressions();

  return (
    <div className="page">
      <div className="section-header">
        <span className="section-num">RG</span>
        <h1 className="display-md">REGRESSION ANALYSIS</h1>
        <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
          {reports.length} REPORT{reports.length !== 1 ? "S" : ""}
        </span>
      </div>

      <p style={{ marginBottom: "2rem", color: "var(--gray-700)", maxWidth: "600px" }}>
        Automated regression detection between agent versions. Each report compares
        pass rates, surfaces new failures, and highlights critical regressions.
      </p>

      {reports.map((report) => {
        const regressed = report.regression_detected;
        const deltaAbs = Math.abs(report.delta);

        return (
          <div key={report.id} style={{ marginBottom: "2.5rem" }}>
            {/* Regression Alert Banner */}
            {regressed && (
              <div
                style={{
                  background: "var(--red)",
                  color: "var(--white)",
                  border: "3px solid var(--black)",
                  padding: "1rem 1.5rem",
                  marginBottom: "0",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  boxShadow: "6px 6px 0 var(--black)",
                }}
              >
                <span style={{ fontSize: "2rem" }}>⚠</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "1.25rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    REGRESSION DETECTED
                  </div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "0.75rem", marginTop: "0.2rem", opacity: 0.85 }}>
                    {report.agent_name} — {report.current_version} vs {report.baseline_version}
                    &nbsp;·&nbsp; {report.critical_regressions} CRITICAL
                  </div>
                </div>
                <div style={{ marginLeft: "auto", textAlign: "right" }}>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "2rem", fontWeight: 700 }}>
                    -{formatPercent(deltaAbs, 1)}
                  </div>
                  <div style={{ fontSize: "0.7rem", opacity: 0.85, letterSpacing: "0.1em" }}>PASS RATE DROP</div>
                </div>
              </div>
            )}

            {!regressed && (
              <div
                style={{
                  background: "var(--green)",
                  color: "var(--black)",
                  border: "3px solid var(--black)",
                  padding: "1rem 1.5rem",
                  marginBottom: "0",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  boxShadow: "6px 6px 0 var(--black)",
                }}
              >
                <span style={{ fontSize: "2rem" }}>✓</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "1.25rem", textTransform: "uppercase" }}>
                    NO REGRESSION
                  </div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: "0.75rem", marginTop: "0.2rem" }}>
                    {report.agent_name} — {report.current_version} maintains or improves on {report.baseline_version}
                  </div>
                </div>
              </div>
            )}

            {/* Version comparison */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto 1fr",
                border: "3px solid var(--black)",
                borderTop: "none",
                boxShadow: "6px 6px 0 var(--black)",
                overflow: "hidden",
              }}
            >
              {/* Baseline */}
              <div
                style={{
                  padding: "2rem",
                  background: "var(--white)",
                  borderRight: "2px solid var(--black)",
                }}
              >
                <div className="label-mono" style={{ color: "var(--gray-500)", marginBottom: "0.5rem" }}>
                  BASELINE
                </div>
                <div style={{ fontWeight: 700, fontSize: "1.25rem", marginBottom: "1rem", textTransform: "uppercase" }}>
                  {report.agent_name} {report.baseline_version}
                </div>
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: "3.5rem",
                    fontWeight: 700,
                    color: "var(--green-dark)",
                    lineHeight: 1,
                  }}
                >
                  {formatPercent(report.baseline_pass_rate)}
                </div>
                <div className="label-mono" style={{ color: "var(--gray-500)", marginTop: "0.25rem" }}>
                  PASS RATE
                </div>
              </div>

              {/* Delta */}
              <div
                style={{
                  padding: "2rem 1.5rem",
                  background: regressed ? "var(--red)" : "var(--green)",
                  color: regressed ? "var(--white)" : "var(--black)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  minWidth: "160px",
                }}
              >
                <div className="label-mono" style={{ opacity: 0.75, marginBottom: "0.5rem" }}>CHANGE</div>
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: "2.5rem",
                    fontWeight: 700,
                    lineHeight: 1,
                  }}
                >
                  {report.delta > 0 ? "+" : ""}{formatPercent(report.delta, 1)}
                </div>
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: "1.5rem",
                    marginTop: "0.5rem",
                  }}
                >
                  {regressed ? "▼" : "▲"}
                </div>
              </div>

              {/* Current */}
              <div
                style={{
                  padding: "2rem",
                  background: regressed ? "#FFF5F5" : "var(--white)",
                  borderLeft: "2px solid var(--black)",
                }}
              >
                <div className="label-mono" style={{ color: "var(--gray-500)", marginBottom: "0.5rem" }}>
                  CURRENT
                </div>
                <div style={{ fontWeight: 700, fontSize: "1.25rem", marginBottom: "1rem", textTransform: "uppercase" }}>
                  {report.agent_name} {report.current_version}
                </div>
                <div
                  style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: "3.5rem",
                    fontWeight: 700,
                    color: regressed ? "var(--red)" : "var(--green-dark)",
                    lineHeight: 1,
                  }}
                >
                  {formatPercent(report.current_pass_rate)}
                </div>
                <div className="label-mono" style={{ color: "var(--gray-500)", marginTop: "0.25rem" }}>
                  PASS RATE
                </div>
              </div>
            </div>

            {/* New Failures */}
            {report.new_failures.length > 0 && (
              <div
                style={{
                  border: "3px solid var(--black)",
                  borderTop: "none",
                  boxShadow: "6px 6px 0 var(--black)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    background: "var(--black)",
                    padding: "0.75rem 1.5rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "'Space Mono', monospace",
                      fontSize: "0.7rem",
                      color: "var(--red)",
                      fontWeight: 700,
                      letterSpacing: "0.1em",
                    }}
                  >
                    ✗ NEW FAILURES ({report.new_failures.length})
                  </span>
                </div>
                <table className="table-brutal" style={{ border: "none" }}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>CATEGORY</th>
                      <th>SCENARIO</th>
                      <th>SEVERITY</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.new_failures.map((tc) => (
                      <tr key={tc.id}>
                        <td className="font-mono" style={{ fontSize: "0.7rem", color: "var(--gray-500)" }}>
                          {tc.id}
                        </td>
                        <td>
                          <span
                            style={{
                              fontFamily: "'Space Mono', monospace",
                              fontSize: "0.7rem",
                              fontWeight: 700,
                              textTransform: "uppercase",
                            }}
                          >
                            {tc.category}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600 }}>{tc.scenario}</td>
                        <td>
                          <span
                            className={`badge ${
                              tc.severity === "critical"
                                ? "badge-fail"
                                : tc.severity === "high"
                                ? "badge-orange"
                                : "badge-warn"
                            }`}
                          >
                            {tc.severity.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Fixed tests */}
            {report.fixed_tests.length > 0 && (
              <div
                style={{
                  border: "3px solid var(--black)",
                  borderTop: "none",
                  padding: "1rem 1.5rem",
                  background: "#F0FFF8",
                }}
              >
                <span className="label-mono" style={{ color: "var(--green-dark)" }}>
                  ✓ {report.fixed_tests.length} PREVIOUSLY FAILING TEST{report.fixed_tests.length > 1 ? "S" : ""} NOW PASSING
                </span>
              </div>
            )}

            {/* Footer */}
            <div
              style={{
                border: "3px solid var(--black)",
                borderTop: "none",
                padding: "1rem 1.5rem",
                background: "var(--gray-100)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "1rem",
                flexWrap: "wrap",
              }}
            >
              <span className="label-mono" style={{ color: "var(--gray-500)" }}>
                Generated: {formatDateTime(report.created_at)}
              </span>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <Link href="/runs" className="btn btn-black btn-sm">
                  VIEW ALL RUNS
                </Link>
                <Link href="/agents" className="btn btn-cream btn-sm">
                  COMPARE AGENTS
                </Link>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
