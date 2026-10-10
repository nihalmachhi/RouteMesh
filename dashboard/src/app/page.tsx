"use client";
import { BackendCards } from "@/components/BackendCards";
import { BehaviorControls } from "@/components/BehaviorControls";
import { DecisionFeed } from "@/components/DecisionFeed";
import { PolicyComparison } from "@/components/PolicyComparison";
import { PolicyControls } from "@/components/PolicyControls";
import { useRouteMesh } from "@/hooks/useRouteMesh";

export default function DashboardPage() {
  const state = useRouteMesh();
  return (
    <main className="mx-auto min-h-screen max-w-7xl px-5 py-8 md:px-10">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="label text-accent">RouteMesh / Operations</p>
          <h1 className="mt-2 text-2xl font-semibold">Traffic routing overview</h1>
          <p className="mt-1 text-sm text-muted">Health, load, latency, and routing decisions</p>
        </div>
        <span className="text-xs text-muted">{state.connected ? "Live stream connected" : "Polling"}</span>
      </header>
      {state.error && <p role="alert" className="mb-5 rounded bg-red-50 p-3 text-sm text-red-800">{state.error}</p>}
      <div className="space-y-5">
        <PolicyControls active={state.policy} onChange={() => void state.refreshNow()} />
        <BackendCards backends={state.backends} />
        <BehaviorControls backendIds={state.backends.map((item) => item.id)} />
        <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <DecisionFeed decisions={state.decisions} />
          <PolicyComparison />
        </div>
      </div>
      <footer className="mt-10 border-t border-line pt-4 text-xs text-muted">
        Policies remain measurable baselines; no performance win is assumed before a controlled run.
      </footer>
    </main>
  );
}
