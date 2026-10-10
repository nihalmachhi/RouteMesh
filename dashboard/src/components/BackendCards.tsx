import type { Backend } from "@/lib/types";

function healthTone(value: Backend["health_state"]): string {
  return value === "HEALTHY" ? "text-accent" : "text-red-700";
}

export function BackendCards({ backends }: { backends: Backend[] }) {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {backends.map((backend) => (
        <article className="card p-5" key={backend.id}>
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold">{backend.id}</h2>
              <p className="mt-1 text-xs text-muted">{backend.url}</p>
            </div>
            <span className={"text-xs font-semibold " + healthTone(backend.health_state)}>
              {backend.health_state}
            </span>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
            <Metric label="Circuit" value={backend.circuit_state.replace("_", " ")} />
            <Metric label="In flight" value={String(backend.in_flight)} />
            <Metric label="Requests" value={String(backend.routed_requests)} />
            <Metric label="EWMA latency" value={backend.ewma_latency_ms.toFixed(1) + " ms"} />
            <Metric label="CPU" value={backend.cpu_percent.toFixed(0) + "%"} />
            <Metric label="Error window" value={(backend.error_rate * 100).toFixed(1) + "%"} />
          </div>
        </article>
      ))}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><p className="label">{label}</p><p className="mt-1">{value}</p></div>;
}
