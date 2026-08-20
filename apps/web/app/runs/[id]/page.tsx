import { getRunDetail, ApiError } from "@/lib/api";
import { formatPercent, formatDateTime, formatLatency, formatDuration, severityColor, statusBadge } from "@/lib/utils";
import Link from "next/link";
import type { Metadata } from "next";
import RunAutoRefresh from "@/components/RunAutoRefresh";

export const metadata: Metadata = {
  title: "Run Detail — Fieldproxy AgentBench",
};

export const dynamic = "force-dynamic";

const STEP_ICONS: Record<string, string> = {
  intent_parsing: "🧠",
  tool_call: "🔧",
  tool_result: "📦",
  decision: "⚡",
  evaluation: "✅",
};

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let run;
  let loadError: unknown = null;
  try {
    run = await getRunDetail(id);
  } catch (e) {
    loadError = e;
  }

  if (!run) {
    const notFound = loadError instanceof ApiError && loadError.status === 404;
    const message =
      loadError instanceof Error ? loadError.message : "UNKNOWN ERROR";
    return (
      <div className="page">
        <div
          className="card-red"
          style={{ maxWidth: "560px", marginTop: "4rem" }}
        >
          <p className="label-mono" style={{ color: "rgba(255,255,255,0.7)", marginBottom: "0.5rem" }}>
            {notFound ? "404 NOT FOUND" : "ERROR"}
          </p>
          <h1 style={{ color: "var(--white)", fontSize: "1.5rem", marginBottom: "0.5rem" }}>
            {notFound ? "RUN NOT FOUND" : "FAILED TO LOAD RUN"}
          </h1>
          <p
            style={{
              color: "rgba(255,255,255,0.8)",
              marginBottom: "1.5rem",
              fontFamily: "var(--font-space-mono), monospace",
              fontSize: "0.8rem",
              wordBreak: "break-word",
            }}
          >
            {notFound ? (
              <>
                Run ID <code>{id}</code> does not exist.
              </>
            ) : (
              message
            )}
          </p>
          <Link href="/runs" className="btn btn-white btn-sm">
            ← BACK TO RUNS
          </Link>
        </div>
      </div>
    );
  }

  const passColor =
    run.pass_rate >= 95 ? "var(--green)" : run.pass_rate >= 80 ? "var(--yellow)" : "var(--red)";

  return (
    <div className="page">
      <RunAutoRefresh status={run.status} />
      {(run.status === "queued" || run.status === "running") && (
        <div
          className="card-yellow"
          style={{
            padding: "1rem 1.5rem",
            marginBottom: "1.5rem",
            fontFamily: "var(--font-space-mono), monospace",
            fontSize: "0.8rem",
            letterSpacing: "0.05em",
          }}
        >
          ⏳ RUN IN PROGRESS — the agent is executing real cases against the
          world. LLM benchmarks take minutes on the free tier; this page
          refreshes automatically.
        </div>
      )}
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.5rem" }}>
        <Link href="/runs" className="label-mono" style={{ color: "var(--gray-500)", textDecoration: "none" }}>
          RUNS
        </Link>
        <span className="label-mono" style={{ color: "var(--gray-300)" }}>→</span>
        <span className="label-mono" style={{ color: "var(--black)" }}>{id}</span>
      </div>

      {/* Header */}
      <div
        style={{
          background: "var(--black)",
          color: "var(--cream)",
          border: "3px solid var(--black)",
          boxShadow: "8px 8px 0 var(--yellow)",
          padding: "2rem",
          marginBottom: "2rem",
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1.5rem",
        }}
      >
        <div>
          <p className="label-mono" style={{ color: "var(--yellow)", marginBottom: "0.4rem" }}>
            BENCHMARK RUN
          </p>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem", textTransform: "uppercase" }}>
            {run.agent_name} {run.agent_version}
          </h1>
          <p style={{ fontFamily: "var(--font-space-mono), monospace", fontSize: "0.75rem", color: "var(--gray-300)" }}>
            {id} &nbsp;·&nbsp; {formatDateTime(run.started_at)}
            {run.completed_at && ` → ${formatDateTime(run.completed_at)}`}
          </p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
            <span className={`badge ${statusBadge(run.status)}`}>
              {run.status.toUpperCase()}
            </span>
            {run.mutation_testing && <span className="badge badge-pink">MUTATION TESTING</span>}
            {run.compare_against && (
              <span className="badge badge-info">vs {run.compare_against}</span>
            )}
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontFamily: "var(--font-space-mono), monospace",
              fontSize: "3.5rem",
              fontWeight: 700,
              color: passColor,
              lineHeight: 1,
            }}
          >
            {formatPercent(run.pass_rate)}
          </div>
          <div className="label-mono" style={{ color: "var(--gray-300)" }}>PASS RATE</div>
          <div style={{ marginTop: "0.5rem", fontFamily: "var(--font-space-mono), monospace", fontSize: "0.8rem", color: "var(--gray-300)" }}>
            {run.passed}/{run.total_tests} &nbsp;·&nbsp; {formatDuration(run.duration_ms)}
          </div>
        </div>
      </div>

      {/* Test Case + Request */}
      <div className="grid-2" style={{ marginBottom: "2rem" }}>
        <div className="card" style={{ padding: "1.5rem" }}>
          <p className="label-mono" style={{ color: "var(--gray-500)", marginBottom: "0.75rem" }}>
            TEST CASE
          </p>
          <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            {run.test_case.scenario}
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--gray-700)", marginBottom: "1rem" }}>
            {run.test_case.description}
          </p>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <span className={`badge ${severityColor(run.test_case.severity)}`}>
              {run.test_case.severity.toUpperCase()}
            </span>
            {run.test_case.tags.map((t) => (
              <span key={t} className="tag">{t}</span>
            ))}
          </div>
        </div>

        <div className="card" style={{ background: "var(--cream)", padding: "1.5rem" }}>
          <p className="label-mono" style={{ color: "var(--gray-500)", marginBottom: "0.75rem" }}>
            AGENT REQUEST
          </p>
          <p
            style={{
              fontFamily: "var(--font-space-mono), monospace",
              fontSize: "0.85rem",
              lineHeight: 1.6,
              color: "var(--black)",
            }}
          >
            &ldquo;{run.agent_request}&rdquo;
          </p>
        </div>
      </div>

      {/* Pipeline Trace */}
      <div style={{ marginBottom: "2rem" }}>
        <div className="section-header">
          <span className="section-num">01</span>
          <h2 style={{ fontSize: "1rem", fontFamily: "var(--font-space-mono), monospace", letterSpacing: "0.1em" }}>
            EXECUTION PIPELINE
          </h2>
          <span className="label-mono" style={{ marginLeft: "auto", color: "var(--gray-500)" }}>
            {run.steps.length} STEPS &nbsp;·&nbsp; {formatLatency(run.latency_ms)} TOTAL
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          {run.steps.map((step, idx) => (
            <div key={step.id} className={`pipeline-step ${step.status}`}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  background:
                    step.status === "pass"
                      ? "var(--green)"
                      : step.status === "fail"
                      ? "var(--red)"
                      : step.status === "running"
                      ? "var(--blue)"
                      : "var(--gray-300)",
                  border: "2px solid var(--black)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  fontFamily: "var(--font-space-mono), monospace",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                }}
              >
                {idx + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "1rem" }}>{STEP_ICONS[step.type] ?? "◆"}</span>
                  <span style={{ fontWeight: 700, fontFamily: "var(--font-space-mono), monospace", fontSize: "0.85rem" }}>
                    {step.name}
                  </span>
                  {step.latency_ms && (
                    <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
                      {formatLatency(step.latency_ms)}
                    </span>
                  )}
                </div>
                {step.output && (
                  <pre
                    style={{
                      background: "rgba(0,0,0,0.04)",
                      border: "1.5px solid var(--gray-200)",
                      padding: "0.75rem",
                      fontSize: "0.72rem",
                      fontFamily: "var(--font-space-mono), monospace",
                      overflowX: "auto",
                      marginTop: "0.4rem",
                      color: "var(--gray-700)",
                    }}
                  >
                    {JSON.stringify(step.output, null, 2)}
                  </pre>
                )}
                {step.error && (
                  <div
                    style={{
                      color: "var(--red)",
                      fontFamily: "var(--font-space-mono), monospace",
                      fontSize: "0.75rem",
                      marginTop: "0.4rem",
                    }}
                  >
                    ✗ {step.error}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Deterministic Evaluation */}
      <div style={{ marginBottom: "2rem" }}>
        <div className="section-header">
          <span className="section-num">02</span>
          <h2 style={{ fontSize: "1rem", fontFamily: "var(--font-space-mono), monospace", letterSpacing: "0.1em" }}>
            DETERMINISTIC EVALUATION
          </h2>
          <span className="label-mono" style={{ marginLeft: "auto", color: "var(--gray-500)" }}>
            {run.evaluation.filter((e) => e.passed).length}/{run.evaluation.length} PASSED
          </span>
        </div>

        <div style={{ border: "3px solid var(--black)", boxShadow: "var(--shadow)", overflow: "auto" }}>
          <table className="table-brutal">
            <thead>
              <tr>
                <th>RULE</th>
                <th>RESULT</th>
                <th>SEVERITY</th>
                <th>EXPECTED</th>
                <th>ACTUAL</th>
                <th>REASON</th>
              </tr>
            </thead>
            <tbody>
              {run.evaluation.map((ev) => (
                <tr key={ev.rule}>
                  <td>
                    <span className="font-mono" style={{ fontWeight: 700, fontSize: "0.8rem" }}>
                      {ev.rule}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${ev.passed ? "badge-pass" : "badge-fail"}`}>
                      {ev.passed ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${severityColor(ev.severity)}`}>
                      {ev.severity.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--gray-700)" }}>{ev.expected}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--gray-700)" }}>{ev.actual}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--gray-700)" }}>{ev.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Agent Decision */}
      {run.agent_decision && (
        <div style={{ marginBottom: "2rem" }}>
          <div className="section-header">
            <span className="section-num">03</span>
            <h2 style={{ fontSize: "1rem", fontFamily: "var(--font-space-mono), monospace", letterSpacing: "0.1em" }}>
              AGENT DECISION
            </h2>
          </div>
          <div className="card" style={{ background: "var(--black)", color: "var(--cream)" }}>
            <pre
              style={{
                fontFamily: "var(--font-space-mono), monospace",
                fontSize: "0.85rem",
                lineHeight: 1.7,
                color: "var(--green)",
              }}
            >
              {JSON.stringify(run.agent_decision, null, 2)}
            </pre>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: "0.75rem" }}>
        <Link href="/runs" className="btn btn-black btn-sm">← ALL RUNS</Link>
        <Link href="/regressions" className="btn btn-cream btn-sm">VIEW REGRESSIONS →</Link>
      </div>
    </div>
  );
}
