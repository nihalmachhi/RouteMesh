import type { Decision } from "@/lib/types";

export function DecisionFeed({ decisions }: { decisions: Decision[] }) {
  return (
    <section className="card overflow-hidden">
      <div className="border-b border-line p-4">
        <h2 className="font-semibold">Recent routing decisions</h2>
        <p className="mt-1 text-xs text-muted">Backend selection and policy explanation</p>
      </div>
      <div className="max-h-[420px] overflow-auto">
        {decisions.map((decision) => (
          <article key={decision.request_id} className="border-b border-line p-4 last:border-0">
            <div className="flex justify-between gap-3">
              <span className="text-sm font-semibold">{decision.chosen_backend_id}</span>
              <span className="text-xs text-muted">{decision.policy}</span>
            </div>
            <p className="mt-1 text-xs text-muted">{decision.reason}</p>
            <p className="mt-1 truncate font-mono text-[10px] text-muted">{decision.request_id}</p>
          </article>
        ))}
        {decisions.length === 0 && <p className="p-4 text-sm text-muted">No requests routed yet.</p>}
      </div>
    </section>
  );
}
