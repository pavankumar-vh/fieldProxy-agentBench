import { getRuns } from "@/lib/api";
import Link from "next/link";
import { formatPercent, formatDateTime, formatDuration, statusBadge } from "@/lib/utils";
import type { Metadata } from "next";
import BenchmarkLauncher from "@/components/BenchmarkLauncher";
import EmptyState from "@/components/EmptyState";

export const metadata: Metadata = {
  title: "Benchmark Runs — Fieldproxy AgentBench",
  description: "View all benchmark runs, launch new benchmarks, and compare agent versions.",
};

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await getRuns();

  return (
    <div className="page">
      <div className="section-header">
        <span className="section-num">RN</span>
        <h1 className="display-md">BENCHMARK RUNS</h1>
        <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
          {runs.length} RUNS
        </span>
      </div>

      {/* Launcher panel */}
      <BenchmarkLauncher />

      {/* Runs table */}
      <div className="section-header" style={{ marginTop: "2.5rem" }}>
        <span className="section-num">02</span>
        <h2 style={{ fontSize: "1rem", fontFamily: "var(--font-space-mono), monospace", letterSpacing: "0.1em" }}>
          RUN HISTORY
        </h2>
      </div>

      {runs.length === 0 ? (
        <EmptyState
          title="NO RUNS"
          message="NO RUNS YET — LAUNCH A BENCHMARK ABOVE TO CREATE ONE."
        />
      ) : (
        <div style={{ border: "3px solid var(--black)", boxShadow: "var(--shadow)", overflow: "auto" }}>
          <table className="table-brutal">
            <thead>
              <tr>
                <th>RUN ID</th>
                <th>AGENT</th>
                <th>VERSION</th>
                <th>STATUS</th>
                <th>PASS RATE</th>
                <th>PASSED</th>
                <th>FAILED</th>
                <th>CRITICAL</th>
                <th>MUTATION</th>
                <th>COMPARE</th>
                <th>DURATION</th>
                <th>STARTED</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--gray-500)" }}>
                      {run.id}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{run.agent_name}</td>
                  <td>
                    <span className="badge badge-black">{run.agent_version}</span>
                  </td>
                  <td>
                    <span className={`badge ${statusBadge(run.status)}`}>
                      {run.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        fontFamily: "var(--font-space-mono), monospace",
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
                  <td className="font-mono" style={{ color: "var(--green-dark)" }}>
                    {run.passed}
                  </td>
                  <td className="font-mono" style={{ color: run.failed > 0 ? "var(--red)" : "var(--gray-500)" }}>
                    {run.failed}
                  </td>
                  <td className="font-mono" style={{ color: run.critical_failures > 0 ? "var(--pink)" : "var(--gray-500)" }}>
                    {run.critical_failures}
                  </td>
                  <td>
                    {run.mutation_testing ? (
                      <span className="badge badge-pink">ON</span>
                    ) : (
                      <span className="badge badge-gray">OFF</span>
                    )}
                  </td>
                  <td>
                    {run.compare_against ? (
                      <span className="badge badge-info">{run.compare_against}</span>
                    ) : (
                      <span style={{ color: "var(--gray-300)" }}>—</span>
                    )}
                  </td>
                  <td className="font-mono" style={{ color: "var(--gray-500)" }}>
                    {formatDuration(run.duration_ms)}
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>
                    {formatDateTime(run.started_at)}
                  </td>
                  <td>
                    <Link href={`/runs/${run.id}`} className="btn btn-black btn-sm">
                      VIEW →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
