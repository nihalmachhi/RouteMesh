import type { PolicyId, SimulatorState } from "@/features/simulator/model";

const cards: { id: PolicyId; title: string; description: string }[] = [
  { id: "round_robin", title: "Round robin", description: "Rotates through healthy candidates with a router-owned counter. Simple and fair, but blind to load." },
  { id: "least_connections", title: "Least connections", description: "Sends each request to the backend with the fewest in-flight requests. Useful when work takes uneven time." },
  { id: "latency_aware", title: "Latency-aware", description: "Scores normalized EWMA latency, CPU, errors, and a small in-flight penalty. Lowest score wins; this is a heuristic, not machine learning." },
];

export function PolicySection({ state, onTryPolicy }: { state: SimulatorState; onTryPolicy: (policy: PolicyId) => void }) {
  return (
    <section className="section wrap" id="policies">
      <SectionHeading title="Three ways to choose. Same traffic." lede="Pick a policy in the simulator, slow one backend down, and watch the same requests land somewhere else." />
      <div className="policy-cards">
        {cards.map((card) => (
          <article className="policy-card" key={card.id}>
            <h3>{card.title}</h3>
            <p>{card.description}</p>
            <div className="policy-visual">
              {card.id === "round_robin" && <div className="round-robin-visual" aria-label="Round robin cycles through three backends"><span>A</span><span>B</span><span>C</span></div>}
              {card.id === "least_connections" && <LeastConnectionsVisual state={state} />}
              {card.id === "latency_aware" && <><div className="weight-bar" role="img" aria-label="Weights: latency 0.5, CPU 0.3, errors 0.2"><span>latency 0.5</span><span>CPU 0.3</span><span>error 0.2</span></div><div className="visual-legend">+ 0.1 in-flight penalty to limit herding</div></>}
            </div>
            <button className="text-link" type="button" onClick={() => onTryPolicy(card.id)}>Try it in the simulator <span aria-hidden="true">→</span></button>
          </article>
        ))}
      </div>
    </section>
  );
}

function LeastConnectionsVisual({ state }: { state: SimulatorState }) {
  return (
    <div className="connection-bars" aria-label="Live in-flight request counts per backend">
      {state.backends.map((backend) => (
        <div className="connection-row" key={backend.id}>
          <span>{backend.id.slice(-1).toUpperCase()}</span><span className="connection-track"><i style={{ width: `${Math.max(6, Math.min(100, backend.inFlight / 6 * 100))}%` }} /></span><b>{backend.inFlight}</b>
        </div>
      ))}
    </div>
  );
}

export function SectionHeading({ title, lede, centered = true }: { title: string; lede?: string; centered?: boolean }) {
  return <div className={centered ? "section-heading centered" : "section-heading"}><h2>{title}</h2>{lede && <p>{lede}</p>}</div>;
}
