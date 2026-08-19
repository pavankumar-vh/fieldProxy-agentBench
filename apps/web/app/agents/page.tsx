import { getAgents } from "@/lib/api";
import Link from "next/link";
import { formatPercent, formatDate, agentStatusBadge } from "@/lib/utils";
import type { Metadata } from "next";
import EmptyState from "@/components/EmptyState";

export const metadata: Metadata = {
  title: "Agents — Fieldproxy AgentBench",
  description: "View all AI agent versions, their benchmark scores, model configuration, and performance history.",
};

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const agents = await getAgents();

  return (
    <div className="page">
      <div className="section-header">
        <span className="section-num">AG</span>
        <h1 className="display-md">AGENTS</h1>
        <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
          {agents.length} REGISTERED
        </span>
      </div>

      <p style={{ marginBottom: "2rem", color: "var(--gray-700)", maxWidth: "600px" }}>
        All registered agent versions. Each version tracks its own model, prompt hash,
        benchmark score, and failure history independently.
      </p>

      {agents.length === 0 ? (
        <EmptyState
          title="NO AGENTS"
          message="NO AGENTS REGISTERED — SEED THE DATABASE TO REGISTER AGENT VERSIONS."
        />
      ) : (
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {agents.map((agent, idx) => {
          const isActive = agent.status === "active";
          const cells: { label: string; value: string; color?: string }[] = [
            { label: "VERSION", value: agent.version },
            {
              label: "ENGINE",
              value:
                agent.engine === "gemini"
                  ? "LLM · Gemini"
                  : agent.engine === "langgraph"
                    ? "LLM · LangGraph"
                    : "Rules",
            },
            { label: "MODEL", value: agent.model },
            { label: "PROMPT HASH", value: agent.prompt_hash },
            { label: "TOTAL TESTS", value: String(agent.total_tests) },
            { label: "PASSED", value: String(agent.passed), color: "var(--green-dark)" },
            {
              label: "FAILED",
              value: String(agent.failed),
              color: agent.failed > 0 ? "var(--red)" : undefined,
            },
            {
              label: "CRITICAL",
              value: String(agent.critical_failures),
              color: agent.critical_failures > 0 ? "var(--red)" : undefined,
            },
            { label: "CREATED", value: formatDate(agent.created_at) },
          ];
          return (
            <div
              key={agent.id}
              className="card"
              style={{
                background: isActive ? "var(--black)" : "var(--white)",
                color: isActive ? "var(--cream)" : "var(--black)",
                boxShadow: isActive ? "8px 8px 0 var(--yellow)" : "var(--shadow)",
                padding: "2rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "1rem",
                  marginBottom: "1.5rem",
                }}
              >
                {/* Left: name + meta */}
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                    <span
                      className="label-mono"
                      style={{ color: isActive ? "var(--yellow)" : "var(--gray-500)" }}
                    >
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <h2
                      style={{
                        fontSize: "1.5rem",
                        fontWeight: 700,
                        letterSpacing: "-0.02em",
                        textTransform: "uppercase",
                      }}
                    >
                      {agent.name}
                    </h2>
                    <span className={`badge ${agentStatusBadge(agent.status)}`}>
                      {agent.status.toUpperCase()}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: "0.875rem",
                      color: isActive ? "var(--gray-300)" : "var(--gray-700)",
                      maxWidth: "500px",
                    }}
                  >
                    {agent.description}
                  </p>
                </div>

                {/* Right: pass rate */}
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontFamily: "var(--font-space-mono), monospace",
                      fontSize: "3rem",
                      fontWeight: 700,
                      lineHeight: 1,
                      color: isActive
                        ? "var(--yellow)"
                        : agent.pass_rate >= 95
                        ? "var(--green-dark)"
                        : agent.pass_rate >= 80
                        ? "var(--orange)"
                        : "var(--red)",
                    }}
                  >
                    {formatPercent(agent.pass_rate)}
                  </div>
                  <div
                    className="label-mono"
                    style={{ color: isActive ? "var(--gray-300)" : "var(--gray-500)" }}
                  >
                    PASS RATE
                  </div>
                </div>
              </div>

              {/* Metadata grid — uniform 1.5px hairlines at any column count
                  via gaps that show the grid's own background */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                  gap: "1.5px",
                  background: isActive ? "var(--gray-700)" : "var(--gray-200)",
                  border: isActive ? "2px solid var(--gray-700)" : "2px solid var(--black)",
                  marginBottom: "1.5rem",
                }}
              >
                {cells.map(({ label, value, color }) => (
                  <div
                    key={label}
                    style={{
                      padding: "0.875rem 1rem",
                      background: isActive ? "var(--black)" : "var(--white)",
                    }}
                  >
                    <div
                      className="label-mono"
                      style={{
                        color: isActive ? "var(--gray-300)" : "var(--gray-500)",
                        fontSize: "0.6rem",
                        marginBottom: "0.25rem",
                      }}
                    >
                      {label}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-space-mono), monospace",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: color ?? (isActive ? "var(--cream)" : "var(--black)"),
                      }}
                    >
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pass rate bar */}
              <div style={{ marginBottom: "1.5rem" }}>
                <div
                  className="label-mono"
                  style={{
                    color: isActive ? "var(--gray-300)" : "var(--gray-500)",
                    marginBottom: "0.5rem",
                  }}
                >
                  BENCHMARK SCORE
                </div>
                <div
                  className="progress-track"
                  style={{
                    background: isActive ? "var(--gray-700)" : "var(--gray-200)",
                    border: isActive
                      ? "2px solid var(--gray-700)"
                      : "2px solid var(--black)",
                  }}
                >
                  <div
                    className="progress-fill"
                    style={{
                      width: `${agent.pass_rate}%`,
                      background:
                        agent.pass_rate >= 95
                          ? "var(--green)"
                          : agent.pass_rate >= 80
                          ? "var(--yellow)"
                          : "var(--red)",
                    }}
                  />
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <Link href="/runs" className={`btn ${isActive ? "btn-yellow" : "btn-black"} btn-sm`}>
                  VIEW RUNS →
                </Link>
                <Link href="/regressions" className={`btn ${isActive ? "btn-cream" : "btn-cream"} btn-sm`}>
                  COMPARE VERSIONS
                </Link>
                {!isActive && (
                  <span
                    className="btn btn-sm"
                    style={{
                      background: "var(--gray-100)",
                      color: "var(--gray-500)",
                      cursor: "not-allowed",
                      boxShadow: "none",
                    }}
                  >
                    {agent.status.toUpperCase()}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
}
