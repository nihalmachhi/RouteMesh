import type { BackendMode } from "@/features/simulator/model";

export function FailureSection({ onBreak }: { onBreak: (backendId: string, mode: BackendMode) => void }) {
  return (
    <section className="section wrap" id="failure">
      <div className="split-layout">
        <div>
          <h2>When a backend breaks, traffic moves.</h2>
          <p className="section-lede">Active health checks and a circuit breaker take a failing backend out of rotation. Probe requests can bring it back after recovery.</p>
          <dl className="fact-list">
            <div><dt>Health checks</dt><dd>Run every 2 seconds. Three failures mark a backend unhealthy; two successes restore it.</dd></div>
            <div><dt>Circuit breaker</dt><dd>Opens after five consecutive failures or a 50% error rate over 20 requests. It stays open for 10 seconds before probing.</dd></div>
            <div><dt>What clients see</dt><dd>503 with Retry-After when no backend is eligible, 504 on a forward timeout, and 502 on connection failure.</dd></div>
          </dl>
          <div className="button-row">
            <button className="button button-dark button-small" type="button" onClick={() => onBreak("backend-b", "failing")}>Make backend-b fail</button>
            <button className="button button-quiet button-small" type="button" onClick={() => onBreak("backend-c", "down")}>Take backend-c down</button>
          </div>
        </div>
        <div className="ui breaker-panel">
          <div className="feed breaker-feed">
            <h3>Breaker states</h3>
            <ol>
              <li><span className="pill ok">closed</span><span className="breaker-copy">Requests flow. Failures are counted.</span></li>
              <li><span className="pill bad">open</span><span className="breaker-copy">Traffic is stopped temporarily after repeated or frequent failures.</span></li>
              <li><span className="pill warn">half-open</span><span className="breaker-copy">Probe requests check recovery; a failure reopens the circuit.</span></li>
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}
