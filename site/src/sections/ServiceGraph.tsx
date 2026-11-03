import { useState } from "react";

interface ServiceGraphProps {
  evidence: {
    maximum_attempts_per_downstream_call: number;
    inventory_failure_blast_radius: string[];
    critical_path_ms: number;
  };
}

const services = ["client", "gateway", "catalog", "inventory"];

export function ServiceGraph({ evidence }: ServiceGraphProps) {
  const [inventoryFailed, setInventoryFailed] = useState(false);
  const affected = new Set(evidence.inventory_failure_blast_radius);

  return (
    <section className="sec" id="graph">
      <h2>Follow a failure. <span className="m">See who depends on it.</span></h2>
      <p className="lead2">A small service graph makes retry amplification and upstream impact visible.</p>
      <div className="sc">
        <article className="scc">
          <h3>Three-tier request path</h3>
          <svg className="flow" viewBox="0 0 760 150" role="img" aria-labelledby="graph-title graph-desc">
            <title id="graph-title">RouteMesh service dependency graph</title>
            <desc id="graph-desc">Client calls gateway, gateway calls catalog, and catalog calls inventory.</desc>
            <path className="fl" d="M150 72H610" />
            {services.map((service, index) => (
              <g className={inventoryFailed && affected.has(service) ? "st last" : "st"} key={service}>
                <rect x={index * 200 + 20} y="46" width="130" height="52" rx="12" />
                <text x={index * 200 + 85} y="77" textAnchor="middle">{service}</text>
              </g>
            ))}
          </svg>
          <button
            aria-pressed={inventoryFailed}
            className="pill"
            onClick={() => setInventoryFailed((failed) => !failed)}
            type="button"
          >
            {inventoryFailed ? "Restore inventory" : "Fail inventory"}
          </button>
          <p aria-live="polite" className="tx">
            {inventoryFailed
              ? `Affected callers: ${[...affected].join(" → ")}.`
              : "All services are available in this graph scenario."}
          </p>
        </article>
        <article className="scc">
          <span className="eyebrow">GENERATED GRAPH EVIDENCE</span>
          <h3>Retries multiply downstream work</h3>
          <div className="mini">
            <b>{evidence.maximum_attempts_per_downstream_call}×</b> maximum path attempt multiplier
            <br />
            <b>{evidence.critical_path_ms} ms</b> critical path in this synthetic graph
          </div>
          <p className="fineprint">Computed from the service graph during `make reproduce`; not a production measurement.</p>
        </article>
      </div>
    </section>
  );
}
