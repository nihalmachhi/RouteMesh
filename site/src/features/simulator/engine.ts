export type PolicyName = "round_robin" | "least_connections" | "latency_aware";

export interface BackendSignal {
  backend_id: string;
  url: string;
  healthy: boolean;
  circuit_state: "closed" | "open" | "half_open";
  in_flight: number;
  ewma_latency_ms: number;
  cpu_percent: number;
  error_rate: number;
  failure_rate: number;
}

export interface CandidateScore {
  backend_id: string;
  score: number;
  in_flight: number;
  ewma_latency_ms: number;
  cpu_percent: number;
  error_rate: number;
}

export interface RoutingDecision {
  request_id: string;
  policy: PolicyName;
  chosen_backend_id: string;
  reason: string;
  candidates: CandidateScore[];
}

export interface PolicyWeights {
  w_latency: number;
  w_cpu: number;
  w_error: number;
  w_in_flight?: number;
}

export interface SimulationInput {
  policy: PolicyName;
  backends: BackendSignal[];
  requestCount: number;
  arrivalRate: number;
  seed?: number;
  weights?: PolicyWeights;
}

export interface BackendShare {
  backend_id: string;
  count: number;
  percentage: number;
  circuit_state: "closed" | "open" | "half_open";
}

export interface DecisionEvent {
  request_id: string;
  backend_id: string | null;
  policy: PolicyName;
  reason: string;
  succeeded: boolean;
  latency_ms: number;
}

export interface SimulationResult {
  policy: PolicyName;
  total: number;
  errors: number;
  errorRate: number;
  p50: number;
  p99: number;
  shares: BackendShare[];
  feed: DecisionEvent[];
}

export class NoHealthyBackendError extends Error {
  constructor() {
    super("no healthy backend is currently eligible");
    this.name = "NoHealthyBackendError";
  }
}

function normalize(values: number[]): number[] {
  if (values.length === 0) return [];
  const low = Math.min(...values);
  const high = Math.max(...values);
  if (high === low) return values.map(() => 0);
  return values.map((value) => (value - low) / (high - low));
}

export function selectBackend(
  policy: PolicyName,
  candidates: BackendSignal[],
  requestId: string,
  rotation: number,
  weights: PolicyWeights = { w_latency: 0.5, w_cpu: 0.3, w_error: 0.2 },
): RoutingDecision {
  const eligible = candidates
    .filter((candidate) => candidate.healthy && candidate.circuit_state !== "open")
    .slice()
    .sort((left, right) => left.backend_id.localeCompare(right.backend_id));

  if (eligible.length === 0) throw new NoHealthyBackendError();

  let scores: CandidateScore[];
  let chosen: CandidateScore;

  if (policy === "round_robin") {
    scores = eligible.map((candidate, index) => ({
      backend_id: candidate.backend_id,
      score: index,
      in_flight: candidate.in_flight,
      ewma_latency_ms: candidate.ewma_latency_ms,
      cpu_percent: candidate.cpu_percent,
      error_rate: candidate.error_rate,
    }));
    chosen = scores[rotation % scores.length]!;
    return {
      request_id: requestId,
      policy,
      chosen_backend_id: chosen.backend_id,
      reason: "next healthy backend in rotation",
      candidates: scores,
    };
  }

  if (policy === "least_connections") {
    const ordered = eligible.slice().sort(
      (left, right) =>
        left.in_flight - right.in_flight || left.backend_id.localeCompare(right.backend_id),
    );
    scores = ordered.map((candidate) => ({
      backend_id: candidate.backend_id,
      score: candidate.in_flight,
      in_flight: candidate.in_flight,
      ewma_latency_ms: candidate.ewma_latency_ms,
      cpu_percent: candidate.cpu_percent,
      error_rate: candidate.error_rate,
    }));
    chosen = scores[0]!;
    return {
      request_id: requestId,
      policy,
      chosen_backend_id: chosen.backend_id,
      reason: "fewest in-flight requests (" + chosen.in_flight + ")",
      candidates: scores,
    };
  }

  const latencies = normalize(eligible.map((candidate) => candidate.ewma_latency_ms));
  const cpu = normalize(eligible.map((candidate) => candidate.cpu_percent));
  const errors = normalize(eligible.map((candidate) => candidate.error_rate));
  const loads = normalize(eligible.map((candidate) => candidate.in_flight));
  const loadWeight = weights.w_in_flight ?? 0.1;
  scores = eligible.map((candidate, index) => ({
    backend_id: candidate.backend_id,
    score:
      weights.w_latency * latencies[index]! +
      weights.w_cpu * cpu[index]! +
      weights.w_error * errors[index]! +
      loadWeight * loads[index]!,
    in_flight: candidate.in_flight,
    ewma_latency_ms: candidate.ewma_latency_ms,
    cpu_percent: candidate.cpu_percent,
    error_rate: candidate.error_rate,
  }));
  const ranked = scores.slice().sort(
    (left, right) =>
      left.score - right.score ||
      left.in_flight - right.in_flight ||
      left.backend_id.localeCompare(right.backend_id),
  );
  chosen = ranked[0]!;
  return {
    request_id: requestId,
    policy,
    chosen_backend_id: chosen.backend_id,
    reason:
      "lowest weighted score " +
      chosen.score.toFixed(3) +
      "; in-flight penalty mitigates herding",
    candidates: scores,
  };
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function percentile(sorted: number[], point: number): number {
  if (sorted.length === 0) return 0;
  const index = Math.min(sorted.length - 1, Math.ceil(point * sorted.length) - 1);
  return sorted[index]!;
}

export function runSimulation(input: SimulationInput): SimulationResult {
  const count = Math.max(1, Math.min(120, Math.floor(input.requestCount)));
  const arrivalRate = Math.max(1, Math.min(100, input.arrivalRate));
  const weights = input.weights ?? { w_latency: 0.5, w_cpu: 0.3, w_error: 0.2 };
  const random = mulberry32(input.seed ?? 2026);
  const backends = input.backends.map((backend) => ({ ...backend, in_flight: 0 }));
  const schedule: { backend_id: string; complete_at: number }[] = [];
  const byId = new Map(backends.map((backend) => [backend.backend_id, backend]));
  const counts = new Map(backends.map((backend) => [backend.backend_id, 0]));
  const outcomes = new Map(backends.map((backend) => [backend.backend_id, [] as boolean[]]));
  const consecutiveFailures = new Map(backends.map((backend) => [backend.backend_id, 0]));
  const openUntil = new Map(backends.map((backend) => [backend.backend_id, 0]));
  const latencies: number[] = [];
  const feed: DecisionEvent[] = [];
  let errors = 0;
  let rotation = 0;

  for (let index = 0; index < count; index += 1) {
    const now = (index * 1000) / arrivalRate;
    for (let cursor = schedule.length - 1; cursor >= 0; cursor -= 1) {
      if (schedule[cursor]!.complete_at <= now) {
        const completed = schedule[cursor]!;
        const backend = byId.get(completed.backend_id);
        if (backend) backend.in_flight = Math.max(0, backend.in_flight - 1);
        schedule.splice(cursor, 1);
      }
    }

    for (const backend of backends) {
      if (backend.healthy && backend.circuit_state === "open" && now >= (openUntil.get(backend.backend_id) ?? 0)) {
        backend.circuit_state = "half_open";
      }
    }

    const candidates = backends.filter(
      (backend) => backend.healthy && backend.circuit_state !== "open",
    );
    const requestId = "req-" + String(index + 1).padStart(3, "0");

    if (candidates.length === 0) {
      errors += 1;
      feed.push({
        request_id: requestId,
        backend_id: null,
        policy: input.policy,
        reason: "no healthy backend is currently eligible",
        succeeded: false,
        latency_ms: 0,
      });
      continue;
    }

    const decision = selectBackend(input.policy, candidates, requestId, rotation, weights);
    rotation += 1;
    const chosen = byId.get(decision.chosen_backend_id)!;
    chosen.in_flight += 1;
    counts.set(chosen.backend_id, (counts.get(chosen.backend_id) ?? 0) + 1);

    const duration = Math.max(
      1,
      chosen.ewma_latency_ms * (0.82 + random() * 0.36) * (1 + chosen.cpu_percent / 500),
    );
    const succeeded = random() >= chosen.failure_rate;
    latencies.push(duration);
    if (!succeeded) errors += 1;
    schedule.push({ backend_id: chosen.backend_id, complete_at: now + duration });

    const history = outcomes.get(chosen.backend_id)!;
    history.push(succeeded);
    if (history.length > 20) history.shift();
    const measuredErrors = history.filter((outcome) => !outcome).length / history.length;
    chosen.error_rate = measuredErrors;
    const streak = succeeded ? 0 : (consecutiveFailures.get(chosen.backend_id) ?? 0) + 1;
    consecutiveFailures.set(chosen.backend_id, streak);

    if (chosen.circuit_state === "half_open") {
      if (succeeded) {
        chosen.circuit_state = "closed";
        consecutiveFailures.set(chosen.backend_id, 0);
      } else {
        chosen.circuit_state = "open";
        openUntil.set(chosen.backend_id, now + 10000);
      }
    } else if (streak >= 5 || (history.length >= 20 && measuredErrors > 0.5)) {
      chosen.circuit_state = "open";
      openUntil.set(chosen.backend_id, now + 10000);
    }

    feed.push({
      request_id: requestId,
      backend_id: chosen.backend_id,
      policy: input.policy,
      reason: decision.reason,
      succeeded,
      latency_ms: duration,
    });
  }

  const orderedLatencies = latencies.slice().sort((left, right) => left - right);
  return {
    policy: input.policy,
    total: count,
    errors,
    errorRate: errors / count,
    p50: percentile(orderedLatencies, 0.5),
    p99: percentile(orderedLatencies, 0.99),
    shares: backends.map((backend) => {
      const served = counts.get(backend.backend_id) ?? 0;
      return {
        backend_id: backend.backend_id,
        count: served,
        percentage: (served / count) * 100,
        circuit_state: backend.circuit_state,
      };
    }),
    feed: feed.slice(-6).reverse(),
  };
}