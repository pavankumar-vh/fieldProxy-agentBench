// ─── API CLIENT ───────────────────────────────────────────
// Real API by default. Set NEXT_PUBLIC_USE_FIXTURES=true to fall back to
// the static fixture data (UI development only).

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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const USE_FIXTURES = process.env.NEXT_PUBLIC_USE_FIXTURES === "true";
const REQUEST_TIMEOUT_MS = 10000;

/** API failure carrying the HTTP status (0 for network/timeout errors). */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "TimeoutError") {
      throw new ApiError(`API ${path} → TIMEOUT AFTER ${timeoutMs / 1000}S`, 0);
    }
    throw new ApiError(`API ${path} → NETWORK ERROR`, 0);
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body: unknown = await res.json();
      if (
        body !== null &&
        typeof body === "object" &&
        "detail" in body &&
        typeof (body as { detail: unknown }).detail === "string"
      ) {
        detail = (body as { detail: string }).detail;
      }
    } catch {
      // Non-JSON error body — the status line above is enough.
    }
    throw new ApiError(
      `API ${path} → ${res.status}${detail ? `: ${detail}` : ""}`,
      res.status
    );
  }

  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(`API ${path} → INVALID JSON IN RESPONSE`, res.status);
  }
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
    if (!r) throw new ApiError(`Run ${id} not found`, 404);
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
  // Runs execute inline on the server; LLM benchmarks make dozens of real
  // Gemini round-trips and can take minutes — give the call 10 minutes.
  return apiFetch<{ run_id: string }>(
    "/benchmark/run",
    { method: "POST", body: JSON.stringify(req) },
    10 * 60 * 1000
  );
}

// ── Regression ─────────────────────────────────────────────
export async function getRegressions(): Promise<RegressionReport[]> {
  if (USE_FIXTURES) return [regressionReport];
  return apiFetch<RegressionReport[]>("/regressions");
}
