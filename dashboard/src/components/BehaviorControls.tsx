"use client";

import { useState } from "react";
import { changeBehavior } from "@/lib/api";
import type { Behavior } from "@/lib/types";

const normal: Behavior = {
  latency_ms: 5, jitter_ms: 0, error_rate: 0, cpu_percent: 15, down: false,
};

export function BehaviorControls({ backendIds }: { backendIds: string[] }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function apply(id: string, behavior: Behavior) {
    setBusy(id);
    setMessage(null);
    try {
      await changeBehavior(id, behavior);
      setMessage(id + " behavior updated");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Backend control failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="card p-5">
      <h2 className="font-semibold">Demo controls</h2>
      <p className="mt-1 text-sm text-muted">Inject a slow, failing, or unavailable backend.</p>
      <div className="mt-4 flex flex-wrap gap-3">
        {backendIds.map((id) => (
          <div key={id} className="flex flex-wrap gap-2 border-r border-line pr-3">
            <span className="self-center text-xs font-semibold">{id}</span>
            <button disabled={busy !== null} onClick={() => void apply(id, { ...normal, latency_ms: 250, cpu_percent: 90 })}
              className="rounded border border-line px-2 py-1 text-xs disabled:opacity-50">Slow</button>
            <button disabled={busy !== null} onClick={() => void apply(id, { ...normal, error_rate: 0.6 })}
              className="rounded border border-line px-2 py-1 text-xs disabled:opacity-50">Failing</button>
            <button disabled={busy !== null} onClick={() => void apply(id, { ...normal, down: true })}
              className="rounded border border-line px-2 py-1 text-xs disabled:opacity-50">Down</button>
            <button disabled={busy !== null} onClick={() => void apply(id, normal)}
              className="rounded border border-line px-2 py-1 text-xs disabled:opacity-50">Reset</button>
          </div>
        ))}
      </div>
      {message && <p className="mt-3 text-xs text-muted" role="status">{message}</p>}
    </section>
  );
}
