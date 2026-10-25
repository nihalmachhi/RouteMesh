import { SimulatorDashboard } from "@/components/simulator/SimulatorDashboard";
import type { BackendMode, PolicyId, SimulatorState } from "@/features/simulator/model";

export function HeroSection({ state, onPolicy, onAuto, onBurst, onReset, onBackendMode }: {
  state: SimulatorState;
  onPolicy: (policy: PolicyId) => void;
  onAuto: () => void;
  onBurst: () => void;
  onReset: () => void;
  onBackendMode: (id: string, mode: BackendMode) => void;
}) {
  return (
    <section className="hero wrap" id="top">
      <p className="eyebrow">Observable application-level routing</p>
      <h1>Send every request to the <span className="healthy-word">healthiest</span> backend. <span className="quiet-words">And see why.</span></h1>
      <p className="hero-subtitle">RouteMesh picks a backend for each request using health, circuit state, latency, CPU, errors, and in-flight work, then records the reason for every choice.</p>
      <div className="button-row centered-actions">
        <a className="button button-dark" href="https://github.com/nihalmachhi/RouteMesh" target="_blank" rel="noreferrer">View on GitHub <span aria-hidden="true">↗</span></a>
        <a className="button button-quiet" href="#start">Run it locally <span aria-hidden="true">↓</span></a>
      </div>
      <p className="hero-note">One command with Docker Compose. A single-process learning system, not a production benchmark.</p>
      <div className="stage" id="demo">
        <SimulatorDashboard state={state} onPolicy={onPolicy} onAuto={onAuto} onBurst={onBurst} onReset={onReset} onBackendMode={onBackendMode} />
        <p className="simulator-note">This simulator runs in your browser and illustrates RouteMesh routing, EWMA scoring, health checks, and circuit breakers. Timings are stretched to show in-flight work; retries and backpressure are not modeled here.</p>
      </div>
    </section>
  );
}
