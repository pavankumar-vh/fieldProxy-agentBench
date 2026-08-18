// ─── TYPES ────────────────────────────────────────────────
// This is the shared type layer. During Phase 1, all data comes from fixtures.
// During Phase 2, these same types are used against real API responses.

export type AgentStatus = "active" | "deprecated" | "draft";
export type RunStatus = "queued" | "running" | "completed" | "failed";
export type TestResult = "pass" | "fail" | "error" | "skipped";
export type Severity = "critical" | "high" | "medium" | "low";
export type TestCategory =
  | "dispatch"
  | "certification"
  | "availability"
  | "inventory"
  | "scheduling"
  | "sla";

export interface AgentVersion {
  id: string;
  name: string;
  version: string;
  model: string;
  prompt_hash: string;
  pass_rate: number;
  total_tests: number;
  passed: number;
  failed: number;
  critical_failures: number;
  status: AgentStatus;
  created_at: string;
  description?: string;
}

export interface TestCase {
  id: string;
  category: TestCategory;
  scenario: string;
  description: string;
  expected_outcome: string;
  severity: Severity;
  last_result: TestResult | null;
  last_run_at: string | null;
  tags: string[];
  is_mutation: boolean;
  parent_id?: string;
}

export interface BenchmarkRun {
  id: string;
  agent_version_id: string;
  agent_name: string;
  agent_version: string;
  status: RunStatus;
  total_tests: number;
  passed: number;
  failed: number;
  critical_failures: number;
  pass_rate: number;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  mutation_testing: boolean;
  compare_against?: string;
  triggered_by: string;
}

export interface AgentStep {
  id: string;
  step_index: number;
  type: "intent_parsing" | "tool_call" | "tool_result" | "decision" | "evaluation";
  name: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  status: "pass" | "fail" | "running" | "pending";
  latency_ms?: number;
  error?: string;
}

export interface EvaluationResult {
  rule: string;
  passed: boolean;
  severity: Severity;
  expected: string;
  actual: string;
  reason: string;
}

export interface RunDetail extends BenchmarkRun {
  test_case: TestCase;
  steps: AgentStep[];
  evaluation: EvaluationResult[];
  agent_request: string;
  agent_decision: Record<string, unknown> | null;
  latency_ms: number;
  error?: string;
}

export interface RegressionReport {
  id: string;
  agent_name: string;
  baseline_version: string;
  current_version: string;
  baseline_pass_rate: number;
  current_pass_rate: number;
  delta: number;
  regression_detected: boolean;
  new_failures: TestCase[];
  fixed_tests: TestCase[];
  critical_regressions: number;
  created_at: string;
}

export interface DashboardMetrics {
  agent_reliability: number;
  total_test_cases: number;
  passed: number;
  failed: number;
  critical: number;
  last_run_at: string | null;
  active_agents: number;
  total_runs: number;
}
