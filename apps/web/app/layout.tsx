import type { Metadata } from "next";
import { Space_Grotesk, Space_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

// Space Mono is a static font (400/700). Space Grotesk is a variable font —
// omitting `weight` loads the full 300–700 axis, covering every weight in
// globals.css (400/500/600/700) with identical rendering.
const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-space-mono",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

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
    <html lang="en" className={`${spaceMono.variable} ${spaceGrotesk.variable}`}>
      <body>
        <div className="app-shell">
          <Navbar />
          <div className="app-content">
            <div className="disclaimer-bar">
              ⚠ NOT AFFILIATED WITH OR INTEGRATED INTO FIELDPROXY &nbsp;·&nbsp;
              INDEPENDENT PROTOTYPE &nbsp;·&nbsp; FOR DEMONSTRATION PURPOSES ONLY
            </div>
            <main>{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
