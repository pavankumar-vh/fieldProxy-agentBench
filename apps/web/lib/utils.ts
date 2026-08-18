export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(ms: number | null): string {
  if (!ms) return "—";
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${minutes}m ${rem}s`;
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "badge-fail";
    case "high": return "badge-orange";
    case "medium": return "badge-warn";
    case "low": return "badge-gray";
    default: return "badge-gray";
  }
}

export function resultBadge(result: string | null): string {
  switch (result) {
    case "pass": return "badge-pass";
    case "fail": return "badge-fail";
    case "error": return "badge-orange";
    case "skipped": return "badge-gray";
    default: return "badge-gray";
  }
}

export function statusBadge(status: string): string {
  switch (status) {
    case "completed": return "badge-pass";
    case "running": return "badge-info";
    case "failed": return "badge-fail";
    case "queued": return "badge-gray";
    default: return "badge-gray";
  }
}

export function agentStatusBadge(status: string): string {
  switch (status) {
    case "active": return "badge-pass";
    case "deprecated": return "badge-gray";
    case "draft": return "badge-warn";
    default: return "badge-gray";
  }
}

export function categoryColor(cat: string): string {
  const map: Record<string, string> = {
    dispatch: "badge-blue",
    certification: "badge-pink",
    availability: "badge-warn",
    inventory: "badge-orange",
    scheduling: "badge-info",
    sla: "badge-fail",
  };
  return map[cat] ?? "badge-gray";
}

export function deltaColor(delta: number): string {
  if (delta > 0) return "#00FF94";
  if (delta < 0) return "#FF1A1A";
  return "#888580";
}
