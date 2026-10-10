"use client";
import { useEffect, useState } from "react";
import type { BenchmarkReport } from "@/lib/types";

export function PolicyComparison() {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/benchmarks/results.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Benchmark report not found");
        return response.json() as Promise<BenchmarkReport>;
      })
      .then(setReport)
      .catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : "Could not load benchmark data"),
      );
  }, []);

  const results = report ? Object.entries(report.results) : [];
  const ceiling = Math.max(1, ...results.map(([, row]) => row.p95_ms));
  return (
    <section className="card p-5">
      <h2 className="font-semibold">Policy comparison</h2>
      {results.length === 0 ? (
        <p className="mt-2 text-sm text-muted">
          {error ?? "No measured results yet. Run make bench to create a report."}
        </p>
      ) : (
        <>
          <div className="mt-4 space-y-3">
            {results.map(([policy, result]) => (
              <div key={policy}>
                <div className="flex justify-between text-xs">
                  <span>{policy.replace("_", " ")}</span>
                  <span>{result.p95_ms.toFixed(1)} ms p95</span>
                </div>
                <progress className="mt-1 h-2 w-full accent-accent" max={ceiling} value={result.p95_ms} aria-label={policy + " p95 latency"} />
                <p className="mt-1 text-[11px] text-muted">
                  p50 {result.p50_ms.toFixed(1)} ms; p99 {result.p99_ms.toFixed(1)} ms;
                  {" " + result.rps.toFixed(1)} req/s; {(result.error_rate * 100).toFixed(2)}% errors
                </p>
              </div>
            ))}
          </div>
          {report?.conditions && (
            <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
              Conditions: {Object.entries(report.conditions)
                .map(([key, value]) => key + " " + value).join(" | ")}
            </p>
          )}
        </>
      )}
    </section>
  );
}
