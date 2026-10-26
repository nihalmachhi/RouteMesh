import { averageSuccessfulLatency, type PolicyId, type SimulatorState } from "@/features/simulator/model";
import { BackendCard } from "./BackendCard";
import { DecisionFeed } from "./DecisionFeed";

const policies: { id: PolicyId; label: string }[] = [
  { id: "round_robin", label: "Round robin" },
  { id: "least_connections", label: "Least connections" },
  { id: "power_of_two_choices", label: "Power of two" },
  { id: "ewma_latency", label: "EWMA latency" },
  { id: "latency_aware", label: "Latency-aware" },
  { id: "thompson_sampling", label: "Thompson sampling" },
];

export function SimulatorDashboard({ state, onPolicy, onAuto, onBurst, onReset, onBackendMode }: {
  state: SimulatorState;
  onPolicy: (policy: PolicyId) => void;
  onAuto: () => void;
  onBurst: () => void;
  onReset: () => void;
  onBackendMode: (id: string, mode: "normal" | "slow" | "failing" | "down") => void;
}) {
  const successRate = state.completedRequests === 0 ? 100 : Math.round((state.successfulRequests / state.completedRequests) * 100);
  const averageLatency = averageSuccessfulLatency(state);

  return (
    <div className="ui simulator" role="group" aria-label="RouteMesh simulated dashboard">
      <div className="ui-bar">
        <div className="ui-title"><span className="live-dot" aria-hidden="true" />RouteMesh <small>simulated dashboard</small></div>
        <div className="kpis" aria-label="Simulation metrics">
          <Kpi value={String(state.requestSequence)} label="requests" />
          <Kpi value={`${successRate}%`} label="succeeded" />
          <Kpi value={`${Math.round(averageLatency)} ms`} label="avg latency" />
        </div>
      </div>
      <div className="sim-controls">
        <div className="policy-switch" role="radiogroup" aria-label="Routing policy">
          {policies.map((policy) => (
            <button key={policy.id} type="button" role="radio" aria-checked={state.policy === policy.id} onClick={() => onPolicy(policy.id)}>
              {policy.label}
            </button>
          ))}
        </div>
        <div className="sim-actions">
          <button className="sim-action" type="button" aria-pressed={state.autoTraffic} onClick={onAuto}>{state.autoTraffic ? "Auto traffic on" : "Auto traffic off"}</button>
          <button className="sim-action primary" type="button" onClick={onBurst}>Send 20 requests</button>
          <button className="sim-action" type="button" onClick={onReset}>Reset</button>
        </div>
      </div>
      <div className="simulator-grid">
        <div className="backend-list">
          {state.backends.map((backend) => <BackendCard key={backend.id} backend={backend} state={state} onModeChange={onBackendMode} />)}
        </div>
        <DecisionFeed state={state} />
      </div>
    </div>
  );
}

function Kpi({ value, label }: { value: string; label: string }) {
  return <div className="kpi"><b>{value}</b><span>{label}</span></div>;
}
