type VisualKind = "metrics" | "dashboard" | "health" | "backpressure" | "forwarding" | "retry" | "policies" | "benchmarks";
const features: { title: string; body: string; kind: VisualKind; wide?: boolean }[] = [
  { title: "Metrics Prometheus can read", body: "Request and error counters use backend, policy, and status-class labels. Scrape them at /metrics.", kind: "metrics", wide: true },
  { title: "Live dashboard", body: "A strict TypeScript React UI streams decisions over SSE.", kind: "dashboard" },
  { title: "Health checks", body: "Checks run every 2 seconds. Three failures mark a backend unhealthy; two successes restore it.", kind: "health" },
  { title: "Backpressure", body: "Admission control caps in-flight requests before they reach the router.", kind: "backpressure" },
  { title: "Safe forwarding", body: "Hop-by-hop headers are removed and request bodies are bounded.", kind: "forwarding" },
  { title: "Retry budget", body: "Only idempotent requests are retried. Up to two attempts share one global budget.", kind: "retry", wide: true },
  { title: "Pure, testable policies", body: "Policies make no network calls or hold global state. They return immutable decisions for deterministic tests.", kind: "policies", wide: true },
  { title: "Reproducible benchmarks", body: "One command runs identical 60-second Locust samples per policy. No measured results are checked in.", kind: "benchmarks", wide: true },
];

export function FeatureGrid() {
  return (
    <section className="section wrap" id="features">
      <div className="section-heading centered"><h2>A whole proxy. One small codebase.</h2><p>Everything around the routing decision helps you see it work: metrics, health checks, limits, and benchmarks.</p></div>
      <div className="feature-grid">
        {features.map((feature) => <article className={`feature-card${feature.wide ? " feature-wide" : ""}`} key={feature.kind}>
          <h3>{feature.title}</h3><p>{feature.body}</p><FeatureVisual kind={feature.kind} />
        </article>)}
      </div>
    </section>
  );
}

function FeatureVisual({ kind }: { kind: VisualKind }) {
  switch (kind) {
    case "metrics": return <div className="feature-visual"><div className="sparkline" aria-label="Illustrative metric activity">{[35,55,42,70,60,82,48,66,90,58,74,50].map((height,index)=><i key={index} style={{height:`${height}%`}} />)}</div><ChipList items={["backend", "policy", "status_class", "GET /metrics"]} /></div>;
    case "dashboard": return <><div className="feature-visual"><div className="signal-dots" aria-hidden="true"><i/><i/><i/><i/></div></div><ChipList items={["SSE", "admin API"]} /></>;
    case "health": return <div className="feature-visual"><div className="health-dots" aria-label="Example health-check outcomes: three pass, two fail, one pass">{[true,true,true,false,false,true].map((ok,index)=><i className={ok?"":"failed"} key={index}/>)}</div><span className="visual-caption">Illustrative sequence</span></div>;
    case "backpressure": return <><div className="feature-visual"><div className="capacity-track"><i /></div></div><ChipList items={["max_in_flight: 500"]} /></>;
    case "forwarding": return <ChipList items={["X-Request-ID", "ROUTEMESH_MAX_BODY_BYTES"]} />;
    case "retry": return <><div className="feature-visual"><ChipList items={["GET", "HEAD", "OPTIONS", "PUT", "DELETE", "Idempotency-Key"]} /></div><ChipList items={["max_attempts: 2", "budget_ratio: 0.1"]} /></>;
    case "policies": return <div className="feature-visual terminal-visual"><b>candidates</b><span>→ immutable snapshots</span><br/><b>policy</b><span>→ backend, score, reason</span><br/><b>router</b><span>→ forwards and records outcome</span></div>;
    case "benchmarks": return <div className="feature-visual terminal-visual"><b>$ make bench</b><br/>round-robin <span>· 60 s</span><br/>least-connections <span>· 60 s</span><br/>latency-aware <span>· 60 s</span><br/><span>→ CSV, JSON, and a p95 chart</span></div>;
  }
}

function ChipList({ items }: { items: string[] }) {
  return <div className="chip-list">{items.map((item) => <span key={item}>{item}</span>)}</div>;
}
