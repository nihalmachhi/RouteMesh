import { type DecisionRecord, type SimulatorState } from "@/features/simulator/model";

function ageLabel(now: number, then: number): string {
  return `+${Math.max(0, (now - then) / 1_000).toFixed(1)}s`;
}

export function DecisionFeed({ state }: { state: SimulatorState }) {
  const decisions = state.decisions.slice(-9).reverse();
  return (
    <section className="feed" aria-label="Recent routing decisions">
      <h3>Decision feed</h3>
      {decisions.length === 0 ? (
        <p className="feed-empty">Requests will appear here as traffic runs.</p>
      ) : (
        <ol>
          {decisions.map((decision) => <DecisionRow key={decision.requestId} decision={decision} now={state.elapsedMs} />)}
        </ol>
      )}
    </section>
  );
}

function DecisionRow({ decision, now }: { decision: DecisionRecord; now: number }) {
  const statusClass = decision.status === null ? "pending" : decision.status < 400 ? "s2" : "s5";
  return (
    <li>
      <span className="time">{ageLabel(now, decision.createdAt)}</span>
      <span>{decision.requestId}</span>
      <span className="destination">{decision.backendId ? `→ ${decision.backendId}` : "✕ rejected"}</span>
      <span className={`status-chip ${statusClass}`}>{decision.status ?? "…"}</span>
      <span className="reason">{decision.reason}</span>
    </li>
  );
}
