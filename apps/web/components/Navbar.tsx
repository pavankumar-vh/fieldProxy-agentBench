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

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <Link href="/" style={{ textDecoration: "none" }}>
          <div className="nav-brand">
            <span className="nav-brand-primary">▶ FIELDPROXY</span>
            <span className="nav-brand-secondary">AgentBench</span>
          </div>
        </Link>

        {/* Nav Links */}
        <ul className="nav-links">
          {links.map(({ href, label, icon: Icon }) => {
            const isActive =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={`nav-link${isActive ? " active" : ""}`}
                >
                  <Icon size={13} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Status pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.35rem 0.75rem",
            border: "2px solid #3D3C38",
            background: "#1a1a1a",
          }}
        >
          <span className="status-dot status-dot-pass" />
          <span
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: "0.65rem",
              color: "#00FF94",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            FIXTURES
          </span>
        </div>
      </div>
    </nav>
  );
}
