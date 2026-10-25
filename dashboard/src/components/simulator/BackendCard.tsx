import { backendCpu, backendStatus, backendTrafficShare, type BackendMode, type BackendState, type SimulatorState } from "@/features/simulator/model";

const modes: BackendMode[] = ["normal", "slow", "failing", "down"];

export function BackendCard({ backend, state, onModeChange }: {
  backend: BackendState;
  state: SimulatorState;
  onModeChange: (id: string, mode: BackendMode) => void;
}) {
  const status = backendStatus(backend, state.elapsedMs);
  const cpu = backendCpu(backend, state.elapsedMs);
  const share = backendTrafficShare(state, backend.id);

  return (
    <article className={`bk${state.latestDecision?.backendId === backend.id ? " hit" : ""}`}>
      <div className="bk-h">
        <h3>{backend.id}</h3>
        <span className={`pill ${status.tone}`}>{status.label}</span>
      </div>
      <dl className="metrics-grid">
        <Metric label="Latency" value={`${Math.round(backend.ewmaLatencyMs)} ms`} />
        <Metric label="CPU" value={`${Math.round(cpu * 100)}%`} progress={cpu * 100} />
        <Metric label="In flight" value={String(backend.inFlight)} />
        <Metric label="Traffic" value={`${Math.round(share * 100)}%`} progress={share * 100} />
      </dl>
      <div className="mode-control" role="radiogroup" aria-label={`${backend.id} simulated behavior`}>
        {modes.map((mode) => (
          <button
            key={mode}
            type="button"
            role="radio"
            aria-checked={backend.mode === mode}
            data-mode={mode}
            onClick={() => onModeChange(backend.id, mode)}
          >
            {mode[0].toUpperCase() + mode.slice(1)}
          </button>
        ))}
      </div>
    </article>
  );
}

function Metric({ label, value, progress }: { label: string; value: string; progress?: number }) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
      {progress !== undefined && <span className="bar" aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} /></span>}
    </div>
  );
}
