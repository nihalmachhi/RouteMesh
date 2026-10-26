const inScope = [
  "One proxy with bounded request bodies and safe headers",
  "Three pure, unit-tested routing policies",
  "Retries for idempotent requests under a shared budget",
  "Prometheus metrics and an SSE-driven React dashboard",
  "make bench for identical 60-second Locust samples per policy",
];
const outOfScope = [
  "Distributed control plane or PostgreSQL",
  "TLS termination, HTTP/2, or WebSocket proxying",
  "Large streaming uploads",
  "Dynamic cloud discovery",
  "Production throughput claims; benchmark results must be measured locally",
];

export function ScopeSection() {
  return (
    <section className="section wrap">
      <div className="section-heading centered"><h2>Built to be understood.</h2><p>RouteMesh is for learning how routing decisions get made, not for carrying production traffic.</p></div>
      <div className="scope-grid">
        <ScopeCard title="In scope" items={inScope} />
        <ScopeCard title="Out of scope" items={outOfScope} />
      </div>
    </section>
  );
}

function ScopeCard({ title, items }: { title: string; items: string[] }) {
  return <article className="scope-card"><h3>{title}</h3><ul>{items.map((item)=><li key={item}>{item}</li>)}</ul></article>;
}
