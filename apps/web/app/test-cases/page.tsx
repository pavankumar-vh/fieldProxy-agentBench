import { getTestCases } from "@/lib/api";
import { formatDateTime, severityColor, resultBadge, categoryColor } from "@/lib/utils";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Test Cases — Fieldproxy AgentBench",
  description: "All benchmark test cases across dispatch, certification, availability, inventory, scheduling, and SLA categories.",
};

export const dynamic = "force-dynamic";

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  dispatch: "End-to-end technician scheduling scenarios",
  certification: "Credential validation and expiry checks",
  availability: "Technician schedule and working-hours checks",
  inventory: "Parts and equipment availability checks",
  scheduling: "Conflict detection and slot management",
  sla: "Service level agreement compliance checks",
};

export default async function TestCasesPage() {
  const cases = await getTestCases();

  const byCategory = cases.reduce(
    (acc, tc) => {
      if (!acc[tc.category]) acc[tc.category] = [];
      acc[tc.category].push(tc);
      return acc;
    },
    {} as Record<string, typeof cases>
  );

  const categories = Object.keys(byCategory);
  const stats = {
    total: cases.length,
    passing: cases.filter((c) => c.last_result === "pass").length,
    failing: cases.filter((c) => c.last_result === "fail").length,
    critical: cases.filter((c) => c.severity === "critical").length,
    mutations: cases.filter((c) => c.is_mutation).length,
  };

  return (
    <div className="page">
      <div className="section-header">
        <span className="section-num">TC</span>
        <h1 className="display-md">TEST CASES</h1>
        <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
          {stats.total} TOTAL
        </span>
      </div>

      {/* Summary row */}
      <div
        style={{
          display: "flex",
          gap: "0",
          border: "3px solid var(--black)",
          boxShadow: "var(--shadow)",
          marginBottom: "2.5rem",
          overflow: "hidden",
        }}
      >
        {[
          { label: "TOTAL", value: stats.total, bg: "var(--black)", fg: "var(--cream)", accent: "var(--yellow)" },
          { label: "PASSING", value: stats.passing, bg: "var(--green)", fg: "var(--black)", accent: "var(--black)" },
          { label: "FAILING", value: stats.failing, bg: "var(--red)", fg: "var(--white)", accent: "var(--white)" },
          { label: "CRITICAL", value: stats.critical, bg: "var(--pink)", fg: "var(--white)", accent: "var(--white)" },
          { label: "MUTATIONS", value: stats.mutations, bg: "var(--cream)", fg: "var(--black)", accent: "var(--blue)" },
        ].map(({ label, value, bg, fg, accent }, i, arr) => (
          <div
            key={label}
            style={{
              flex: 1,
              padding: "1.5rem",
              background: bg,
              color: fg,
              borderRight: i < arr.length - 1 ? "2px solid var(--black)" : "none",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: "2.5rem",
                fontWeight: 700,
                color: accent,
                lineHeight: 1,
              }}
            >
              {value}
            </div>
            <div
              className="label-mono"
              style={{ color: fg === "var(--black)" ? "var(--gray-700)" : "rgba(255,255,255,0.7)", marginTop: "0.25rem" }}
            >
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* By Category */}
      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        {categories.map((cat) => {
          const catCases = byCategory[cat];
          return (
            <div key={cat}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  marginBottom: "1rem",
                  paddingBottom: "0.75rem",
                  borderBottom: "2px solid var(--black)",
                }}
              >
                <span className={`badge ${categoryColor(cat)}`}>
                  {cat.toUpperCase()}
                </span>
                <h2 style={{ fontSize: "1rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  {CATEGORY_DESCRIPTIONS[cat] ?? cat}
                </h2>
                <span className="label-mono" style={{ color: "var(--gray-500)", marginLeft: "auto" }}>
                  {catCases.length} CASES
                </span>
              </div>

              <div style={{ border: "3px solid var(--black)", boxShadow: "var(--shadow)", overflow: "hidden" }}>
                <table className="table-brutal">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>SCENARIO</th>
                      <th>EXPECTED</th>
                      <th>SEVERITY</th>
                      <th>LAST RESULT</th>
                      <th>LAST RUN</th>
                      <th>TAGS</th>
                      <th>TYPE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catCases.map((tc) => (
                      <tr key={tc.id}>
                        <td>
                          <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--gray-500)" }}>
                            {tc.id}
                          </span>
                        </td>
                        <td style={{ maxWidth: "280px" }}>
                          <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "0.2rem" }}>
                            {tc.scenario}
                          </div>
                          <div style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}>
                            {tc.description}
                          </div>
                        </td>
                        <td style={{ maxWidth: "200px", fontSize: "0.8rem", color: "var(--gray-700)" }}>
                          {tc.expected_outcome}
                        </td>
                        <td>
                          <span className={`badge ${severityColor(tc.severity)}`}>
                            {tc.severity.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          {tc.last_result ? (
                            <span className={`badge ${resultBadge(tc.last_result)}`}>
                              {tc.last_result.toUpperCase()}
                            </span>
                          ) : (
                            <span className="badge badge-gray">NEVER RUN</span>
                          )}
                        </td>
                        <td style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}>
                          {tc.last_run_at ? formatDateTime(tc.last_run_at) : "—"}
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                            {tc.tags.map((tag) => (
                              <span key={tag} className="tag">{tag}</span>
                            ))}
                          </div>
                        </td>
                        <td>
                          {tc.is_mutation ? (
                            <span className="badge badge-pink">MUTATION</span>
                          ) : (
                            <span className="badge badge-gray">BASE</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
