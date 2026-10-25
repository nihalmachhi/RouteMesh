import { DecisionInspector } from "@/components/simulator/DecisionInspector";
import type { PolicyId, SimulatorState } from "@/features/simulator/model";

export function DecisionSection({ state, onPolicy }: { state: SimulatorState; onPolicy: (policy: PolicyId) => void }) {
  return (
    <section className="section wrap" id="reasons">
      <div className="split-layout">
        <div className="stage inspector-stage"><DecisionInspector decision={state.latestDecision} /></div>
        <div>
          <h2>Every choice comes with a reason.</h2>
          <p className="section-lede">RouteMesh records which backend won, the scores behind it, and why. This panel shows the latest decision from the simulator above.</p>
          <dl className="fact-list">
            <div><dt>Every request</dt><dd>Gets a request ID for decision logs and admin data, and returns it to the client as <code>X-Request-ID</code>.</dd></div>
            <div><dt>Metrics</dt><dd>Use backend, policy, and status-class labels. Request IDs never become metric labels.</dd></div>
            <div><dt>Dashboard feed</dt><dd>Streams decisions over best-effort SSE. Polling the admin API recovers current state.</dd></div>
          </dl>
          <div className="button-row">
            <button className="button button-dark button-small" type="button" onClick={() => onPolicy("latency_aware")}>Score with latency-aware</button>
            <button className="button button-quiet button-small" type="button" onClick={() => onPolicy("round_robin")}>Compare with round robin</button>
          </div>
        </div>
      </div>
    </section>
  );
}
