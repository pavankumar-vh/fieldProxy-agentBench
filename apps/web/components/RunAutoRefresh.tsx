"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * While a benchmark run is queued/running (LLM benchmarks execute in the
 * background and take minutes), re-fetch this server page every few seconds
 * so results appear live without a manual reload.
 */
export default function RunAutoRefresh({ status }: { status: string }) {
  const router = useRouter();

  useEffect(() => {
    if (status !== "queued" && status !== "running") return;
    const timer = setInterval(() => router.refresh(), 4000);
    return () => clearInterval(timer);
  }, [status, router]);

  return null;
}
