import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Fieldproxy AgentBench — Regression Testing for Field-Service AI",
  description:
    "An independent prototype benchmark harness built around Fieldproxy's publicly documented AI/FSM workflows. Tests, evaluates, and tracks AI agent reliability for field-service management.",
  keywords: ["AI", "benchmark", "field service", "LangGraph", "Gemini", "regression testing"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div className="disclaimer-bar">
          ⚠ NOT AFFILIATED WITH OR INTEGRATED INTO FIELDPROXY &nbsp;·&nbsp;
          INDEPENDENT PROTOTYPE &nbsp;·&nbsp; FOR DEMONSTRATION PURPOSES ONLY
        </div>
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
