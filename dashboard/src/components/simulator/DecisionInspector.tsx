import { type CandidateSnapshot, type DecisionRecord, type PolicyId } from "@/features/simulator/model";

const policyLabels: Record<PolicyId, string> = {
  round_robin: "Round robin",
  least_connections: "Least connections",
  power_of_two_choices: "Power of two choices",
  ewma_latency: "EWMA latency",
  latency_aware: "Latency-aware",
  thompson_sampling: "Thompson sampling",
};

export function DecisionInspector({ decision }: { decision: DecisionRecord | null }) {
  if (!decision?.backendId) {
    return <div className="ui inspector empty-inspector"><p>Send traffic to inspect a routing decision.</p></div>;
  }

  const maxScore = Math.max(0.25, ...decision.candidates.map((candidate) => candidate.score ?? 0));
  const candidates = [...decision.candidates].sort((a, b) => Number(b.backendId === decision.backendId) - Number(a.backendId === decision.backendId));

  return (
    <div className="ui inspector" aria-label="Latest routing decision">
      <div className="inspector-heading">
        <span className="mono">{decision.requestId}</span>
        <span>→ <b>{decision.backendId}</b></span>
        <span className="policy-label">{policyLabels[decision.policy]}</span>
      </div>
      <p className="inspector-reason">{decision.detail}</p>
      <ul className="inspector-list">
        {candidates.map((candidate) => (
          <CandidateRow key={candidate.backendId} candidate={candidate} chosen={candidate.backendId === decision.backendId} policy={decision.policy} maxScore={maxScore} />
        ))}
        {decision.excluded.map((candidate) => (
          <li className="inspector-row excluded" key={candidate.backendId}>
            <div className="inspector-row-heading"><span>{candidate.backendId}</span><span>excluded</span></div>
            <p>{candidate.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CandidateRow({ candidate, chosen, policy, maxScore }: {
  candidate: CandidateSnapshot;
  chosen: boolean;
  policy: PolicyId;
  maxScore: number;
}) {
  const scoreWidth = candidate.score === null ? 0 : Math.max(4, (candidate.score / maxScore) * 100);
  const loadWidth = Math.max(4, Math.min(100, (candidate.inFlight / 6) * 100));
  return (
    <li className={`inspector-row${chosen ? " chosen" : ""}`}>
      <div className="inspector-row-heading">
        <span>{candidate.backendId}{chosen ? " · chosen" : ""}</span>
        <span>{policy === "latency_aware" ? `score ${(candidate.score ?? 0).toFixed(3)}` : policy === "least_connections" || policy === "power_of_two_choices" ? `${candidate.inFlight} in flight` : policy === "ewma_latency" ? `${Math.round(candidate.latencyMs)} ms EWMA` : policy === "thompson_sampling" ? `reward ${((1 - (candidate.score ?? 1))).toFixed(2)}` : ""}</span>
      </div>
      {policy === "latency_aware" && <span className="bar"><i style={{ width: `${scoreWidth}%` }} /></span>}
      {policy === "least_connections" && <span className="bar"><i style={{ width: `${loadWidth}%` }} /></span>}
      {policy === "power_of_two_choices" && candidate.score !== null && <span className="bar"><i style={{ width: `${loadWidth}%` }} /></span>}
      {policy === "thompson_sampling" && <span className="bar"><i style={{ width: `${Math.max(0, Math.min(100, (1 - (candidate.score ?? 1)) * 100))}%` }} /></span>}
      <p>latency {Math.round(candidate.latencyMs)} ms · cpu {Math.round(candidate.cpu * 100)}% · errors {Math.round(candidate.errorRate * 100)}% · in flight {candidate.inFlight}</p>
    </li>
  );
}
