// ─── API CLIENT ───────────────────────────────────────────
// Phase 1: returns fixture data.
// Phase 2: swap USE_FIXTURES=false → hits real FastAPI endpoints.
// Types are identical — no page rewrites needed.

import {
  dashboardMetrics,
  agentVersions,
  testCases,
  benchmarkRuns,
  runDetails,
  regressionReport,
} from "./fixtures";
import type {
  AgentVersion,
  TestCase,
  BenchmarkRun,
  RunDetail,
  RegressionReport,
  DashboardMetrics,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const USE_FIXTURES = true; // Flip to false in Phase 2

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Dashboard ──────────────────────────────────────────────
export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  if (USE_FIXTURES) return dashboardMetrics;
  return apiFetch<DashboardMetrics>("/agents/metrics");
}

// ── Agents ─────────────────────────────────────────────────
export async function getAgents(): Promise<AgentVersion[]> {
  if (USE_FIXTURES) return agentVersions;
  return apiFetch<AgentVersion[]>("/agents");
}

export async function getAgent(id: string): Promise<AgentVersion> {
  if (USE_FIXTURES) {
    const a = agentVersions.find((a) => a.id === id);
    if (!a) throw new Error(`Agent ${id} not found`);
    return a;
  }
  return apiFetch<AgentVersion>(`/agents/${id}`);
}

// ── Test Cases ─────────────────────────────────────────────
export async function getTestCases(): Promise<TestCase[]> {
  if (USE_FIXTURES) return testCases;
  return apiFetch<TestCase[]>("/test-cases");
}

// ── Runs ───────────────────────────────────────────────────
export async function getRuns(): Promise<BenchmarkRun[]> {
  if (USE_FIXTURES) return benchmarkRuns;
  return apiFetch<BenchmarkRun[]>("/runs");
}

export async function getRunDetail(id: string): Promise<RunDetail> {
  if (USE_FIXTURES) {
    const r = runDetails[id];
    if (!r) throw new Error(`Run ${id} not found`);
    return r;
  }
  return apiFetch<RunDetail>(`/runs/${id}`);
}

// ── Benchmark ──────────────────────────────────────────────
export interface BenchmarkRunRequest {
  agent_version_id: string;
  benchmark_type: string;
  mutation_testing: boolean;
  compare_against?: string;
}

export async function startBenchmark(
  req: BenchmarkRunRequest
): Promise<{ run_id: string }> {
  if (USE_FIXTURES) {
    // Simulate a run ID during Phase 1
    return { run_id: "run_001" };
  }
  return apiFetch<{ run_id: string }>("/benchmark/run", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ── Regression ─────────────────────────────────────────────
export async function getRegressions(): Promise<RegressionReport[]> {
  if (USE_FIXTURES) return [regressionReport];
  return apiFetch<RegressionReport[]>("/regressions");
}
