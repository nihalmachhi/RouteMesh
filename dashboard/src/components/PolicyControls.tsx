"use client";

import { useState } from "react";
import { changePolicy } from "@/lib/api";

const policies = ["round_robin", "least_connections", "latency_aware"];

export function PolicyControls({ active, onChange }: { active: string; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function select(policy: string) {
    setBusy(true);
    setError(null);
    try {
      await changePolicy(policy);
      onChange();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Policy update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card flex flex-wrap items-center gap-3 p-4">
      <span className="label mr-2">Active policy</span>
      {policies.map((policy) => (
        <button key={policy} disabled={busy || active === policy} onClick={() => void select(policy)}
          className={"rounded border px-3 py-2 text-xs disabled:opacity-50 " +
            (active === policy ? "border-accent bg-accent text-white" : "border-line bg-white")}>
          {policy.replace("_", " ")}
        </button>
      ))}
      {error && <span role="alert" className="text-xs text-red-700">{error}</span>}
    </section>
  );
}
