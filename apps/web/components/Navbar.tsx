"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  FlaskConical,
  Play,
  GitCompare,
} from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/test-cases", label: "Test Cases", icon: FlaskConical },
  { href: "/runs", label: "Runs", icon: Play },
  { href: "/regressions", label: "Regressions", icon: GitCompare },
];

const FIXTURE_MODE = process.env.NEXT_PUBLIC_USE_FIXTURES === "true";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      {/* Brand */}
      <Link href="/" style={{ textDecoration: "none" }}>
        <div className="sidebar-brand">
          <span className="nav-brand-primary">▶ FIELDPROXY</span>
          <span className="nav-brand-secondary">AgentBench</span>
        </div>
      </Link>

      {/* Nav links */}
      <ul className="sidebar-links">
        {links.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                className={`sidebar-link${isActive ? " active" : ""}`}
              >
                <Icon size={14} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>

      {/* Status footer */}
      <div className="sidebar-footer">
        <div className="status-pill">
          <span
            className={`status-dot ${
              FIXTURE_MODE ? "status-dot-warn" : "status-dot-pass"
            }`}
          />
          <span className="status-pill-label">
            {FIXTURE_MODE ? "Fixtures" : "Live API"}
          </span>
        </div>
        <div className="sidebar-meta">
          Benchmark harness
          <br />
          FastAPI · Postgres · Gemini
        </div>
      </div>
    </aside>
  );
}
