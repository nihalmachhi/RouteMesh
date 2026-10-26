export type PolicyId = "round_robin" | "least_connections" | "power_of_two_choices" | "ewma_latency" | "latency_aware" | "thompson_sampling";
export type BackendMode = "normal" | "slow" | "failing" | "down";
export type BreakerState = "closed" | "open" | "half_open";

export interface CandidateSnapshot {
  backendId: string;
  score: number | null;
  inFlight: number;
  latencyMs: number;
  cpu: number;
  errorRate: number;
}

export interface ExcludedBackend {
  backendId: string;
  reason: string;
}

export interface DecisionRecord {
  sequence: number;
  requestId: string;
  createdAt: number;
  backendId: string | null;
  status: number | null;
  policy: PolicyId;
  reason: string;
  detail: string;
  candidates: CandidateSnapshot[];
  excluded: ExcludedBackend[];
}

export interface BackendState {
  id: string;
  baseLatencyMs: number;
  baseCpu: number;
  mode: BackendMode;
  healthy: boolean;
  healthFailures: number;
  healthSuccesses: number;
  breaker: BreakerState;
  consecutiveFailures: number;
  outcomes: boolean[];
  openUntil: number;
  probeInFlight: boolean;
  probeSuccesses: number;
  ewmaLatencyMs: number;
  inFlight: number;
  routedRequests: number;
}

interface PendingRequest {
  requestId: string;
  backendId: string;
  completesAt: number;
  status: number;
  measuredLatencyMs: number;
  updatesLatency: boolean;
}

export interface SimulatorState {
  elapsedMs: number;
  requestSequence: number;
  roundRobinCursor: number;
  autoTraffic: boolean;
  autoAccumulator: number;
  queuedRequests: number;
  healthAccumulator: number;
  randomSeed: number;
  policy: PolicyId;
  backends: BackendState[];
  pending: PendingRequest[];
  decisions: DecisionRecord[];
  latestDecision: DecisionRecord | null;
  completedRequests: number;
  successfulRequests: number;
  successfulLatencies: number[];
}

const CONFIG = {
  alpha: 0.2,
  weights: { latency: 0.5, cpu: 0.3, error: 0.2, load: 0.1 },
  healthIntervalMs: 2_000,
  unhealthyAfter: 3,
  healthyAfter: 2,
  failuresToOpen: 5,
  errorWindowSize: 20,
  errorThreshold: 0.5,
  breakerOpenMs: 10_000,
  probesToClose: 2,
  timeScale: 6,
};

const BACKEND_SEEDS = [
  { id: "backend-a", latency: 42, cpu: 0.28 },
  { id: "backend-b", latency: 55, cpu: 0.34 },
  { id: "backend-c", latency: 48, cpu: 0.31 },
] as const;

function createBackend(seed: (typeof BACKEND_SEEDS)[number]): BackendState {
  return {
    id: seed.id,
    baseLatencyMs: seed.latency,
    baseCpu: seed.cpu,
    mode: "normal",
    healthy: true,
    healthFailures: 0,
    healthSuccesses: 0,
    breaker: "closed",
    consecutiveFailures: 0,
    outcomes: [],
    openUntil: 0,
    probeInFlight: false,
    probeSuccesses: 0,
    ewmaLatencyMs: seed.latency,
    inFlight: 0,
    routedRequests: 0,
  };
}

export function createSimulator(policy: PolicyId = "latency_aware"): SimulatorState {
  return {
    elapsedMs: 0,
    requestSequence: 0,
    roundRobinCursor: 0,
    autoTraffic: true,
    autoAccumulator: 0,
    queuedRequests: 0,
    healthAccumulator: 0,
    randomSeed: 7,
    policy,
    backends: BACKEND_SEEDS.map(createBackend),
    pending: [],
    decisions: [],
    latestDecision: null,
    completedRequests: 0,
    successfulRequests: 0,
    successfulLatencies: [],
  };
}

function nextRandom(state: SimulatorState): number {
  state.randomSeed = (Math.imul(state.randomSeed, 1_664_525) + 1_013_904_223) >>> 0;
  return state.randomSeed / 4_294_967_296;
}

function errorRate(backend: BackendState): number {
  if (backend.outcomes.length === 0) return 0;
  return backend.outcomes.filter(Boolean).length / backend.outcomes.length;
}

export function backendCpu(backend: BackendState, elapsedMs: number): number {
  if (backend.mode === "down") return 0.02;
  const slowLoad = backend.mode === "slow" ? 0.35 : 0;
  const wobble = 0.03 * Math.sin(elapsedMs / 700 + backend.baseLatencyMs);
  return Math.max(0.02, Math.min(1, backend.baseCpu + backend.inFlight * 0.04 + slowLoad + wobble));
}

export function backendEligible(backend: BackendState): boolean {
  return backend.healthy && (backend.breaker === "closed" || (backend.breaker === "half_open" && !backend.probeInFlight));
}

function snapshot(backend: BackendState, elapsedMs: number, score: number | null = null): CandidateSnapshot {
  return {
    backendId: backend.id,
    score,
    inFlight: backend.inFlight,
    latencyMs: backend.ewmaLatencyMs,
    cpu: backendCpu(backend, elapsedMs),
    errorRate: errorRate(backend),
  };
}

function normalize(value: number, values: number[]): number {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return max === min ? 0 : (value - min) / (max - min);
}

function excludedBackends(backends: BackendState[]): ExcludedBackend[] {
  return backends.filter((backend) => !backendEligible(backend)).map((backend) => ({
    backendId: backend.id,
    reason: !backend.healthy ? "unhealthy" : backend.breaker === "open" ? "circuit open" : "probe already in flight",
  }));
}

function openBreaker(backend: BackendState, elapsedMs: number): void {
  backend.breaker = "open";
  backend.openUntil = elapsedMs + CONFIG.breakerOpenMs;
  backend.probeInFlight = false;
  backend.probeSuccesses = 0;
  backend.consecutiveFailures = 0;
}

function pushDecision(state: SimulatorState, record: DecisionRecord): void {
  state.decisions = [...state.decisions, record].slice(-200);
}

function route(state: SimulatorState, candidates: BackendState[]): { backend: BackendState; reason: string; detail: string; snapshots: CandidateSnapshot[] } {
  if (state.policy === "round_robin") {
    const backend = candidates[state.roundRobinCursor % candidates.length];
    state.roundRobinCursor += 1;
    return {
      backend,
      reason: "next in rotation",
      detail: "next healthy backend in rotation",
      snapshots: candidates.map((candidate) => snapshot(candidate, state.elapsedMs)),
    };
  }

  if (state.policy === "least_connections") {
    const ranked = [...candidates].sort((a, b) => a.inFlight - b.inFlight || a.id.localeCompare(b.id));
    const backend = ranked[0];
    return {
      backend,
      reason: `fewest in-flight (${backend.inFlight})`,
      detail: "fewest in-flight requests",
      snapshots: ranked.map((candidate) => snapshot(candidate, state.elapsedMs)),
    };
  }

  if (state.policy === "power_of_two_choices") {
    const sorted = [...candidates].sort((a, b) => a.id.localeCompare(b.id));
    const hash = [...`req-${state.requestSequence + 1}`].reduce((value, char) => (Math.imul(value, 31) + char.charCodeAt(0)) >>> 0, 0);
    const first = hash % sorted.length;
    const offset = sorted.length < 2 ? 0 : 1 + Math.floor(hash / sorted.length) % (sorted.length - 1);
    const sampled = sorted.length < 2 ? [sorted[first]] : [sorted[first], sorted[(first + offset) % sorted.length]];
    const backend = [...sampled].sort((a, b) => a.inFlight - b.inFlight || a.ewmaLatencyMs - b.ewmaLatencyMs || a.id.localeCompare(b.id))[0];
    const ids = sampled.map((item) => item.id).join(" and ");
    return {
      backend,
      reason: `lower load from ${ids}`,
      detail: `power-of-two sampled ${ids} and chose the lower in-flight count`,
      snapshots: sorted.map((candidate) => snapshot(candidate, state.elapsedMs, sampled.includes(candidate) ? candidate.inFlight : null)),
    };
  }

  if (state.policy === "ewma_latency") {
    const ranked = [...candidates].sort((a, b) => a.ewmaLatencyMs - b.ewmaLatencyMs || a.id.localeCompare(b.id));
    const backend = ranked[0];
    return {
      backend,
      reason: `${Math.round(backend.ewmaLatencyMs)} ms EWMA`,
      detail: `lowest observed EWMA latency (${Math.round(backend.ewmaLatencyMs)} ms)`,
      snapshots: ranked.map((candidate) => snapshot(candidate, state.elapsedMs, candidate.ewmaLatencyMs)),
    };
  }

  if (state.policy === "thompson_sampling") {
    const latencies = candidates.map((backend) => backend.ewmaLatencyMs);
    const ranked = candidates.map((backend, index) => ({
      backend,
      reward: Math.max(0.02, Math.min(0.98, 1 - normalize(latencies[index], latencies))),
    })).sort((a, b) => b.reward - a.reward || a.backend.id.localeCompare(b.backend.id));
    const winner = ranked[0];
    return {
      backend: winner.backend,
      reason: `simulated reward ${winner.reward.toFixed(2)}`,
      detail: `browser illustration selects the current lowest-latency reward estimate (${winner.reward.toFixed(2)}); server Thompson sampling learns from outcomes`,
      snapshots: ranked.map(({ backend, reward }) => snapshot(backend, state.elapsedMs, 1 - reward)),
    };
  }

  const latency = candidates.map((backend) => backend.ewmaLatencyMs);
  const cpu = candidates.map((backend) => backendCpu(backend, state.elapsedMs));
  const errors = candidates.map(errorRate);
  const load = candidates.map((backend) => backend.inFlight);
  const ranked = candidates.map((backend, index) => {
    const score = CONFIG.weights.latency * normalize(latency[index], latency)
      + CONFIG.weights.cpu * normalize(cpu[index], cpu)
      + CONFIG.weights.error * normalize(errors[index], errors)
      + CONFIG.weights.load * normalize(load[index], load);
    return { backend, score };
  }).sort((a, b) => a.score - b.score || a.backend.inFlight - b.backend.inFlight || a.backend.id.localeCompare(b.backend.id));

  const winner = ranked[0];
  return {
    backend: winner.backend,
    reason: `score ${winner.score.toFixed(3)}`,
    detail: `lowest weighted score ${winner.score.toFixed(3)}; in-flight penalty mitigates herding`,
    snapshots: ranked.map(({ backend, score }) => snapshot(backend, state.elapsedMs, score)),
  };
}

function spawnRequest(state: SimulatorState): void {
  state.requestSequence += 1;
  const requestId = `req-${String(state.requestSequence).padStart(4, "0")}`;
  const candidates = state.backends.filter(backendEligible);
  if (candidates.length === 0) {
    const rejected: DecisionRecord = {
      sequence: state.requestSequence,
      requestId,
      createdAt: state.elapsedMs,
      backendId: null,
      status: 503,
      policy: state.policy,
      reason: "no eligible backend",
      detail: "no healthy backend with an available circuit",
      candidates: [],
      excluded: excludedBackends(state.backends),
    };
    pushDecision(state, rejected);
    state.completedRequests += 1;
    return;
  }

  const choice = route(state, candidates);
  const backend = choice.backend;
  const record: DecisionRecord = {
    sequence: state.requestSequence,
    requestId,
    createdAt: state.elapsedMs,
    backendId: backend.id,
    status: null,
    policy: state.policy,
    reason: choice.reason,
    detail: choice.detail,
    candidates: choice.snapshots,
    excluded: excludedBackends(state.backends),
  };
  backend.inFlight += 1;
  backend.routedRequests += 1;
  if (backend.breaker === "half_open") backend.probeInFlight = true;
  pushDecision(state, record);
  state.latestDecision = record;

  let latencyMs = backend.baseLatencyMs * (0.85 + nextRandom(state) * 0.3);
  let status = 200;
  let measured = true;
  let durationMs: number;
  if (backend.mode === "down") {
    status = 502;
    latencyMs = 5;
    measured = false;
    durationMs = 100;
  } else {
    if (backend.mode === "slow") latencyMs *= 6;
    if (backend.mode === "failing" && nextRandom(state) < 0.9) status = 500;
    durationMs = latencyMs * CONFIG.timeScale;
  }
  state.pending.push({
    requestId,
    backendId: backend.id,
    completesAt: state.elapsedMs + durationMs,
    status,
    measuredLatencyMs: latencyMs,
    updatesLatency: measured,
  });
}

function completeRequest(state: SimulatorState, pending: PendingRequest): void {
  const backend = state.backends.find((candidate) => candidate.id === pending.backendId);
  if (!backend) return;
  const failed = pending.status >= 500;
  backend.inFlight = Math.max(0, backend.inFlight - 1);
  if (pending.updatesLatency) {
    backend.ewmaLatencyMs = CONFIG.alpha * pending.measuredLatencyMs + (1 - CONFIG.alpha) * backend.ewmaLatencyMs;
  }
  backend.outcomes = [...backend.outcomes, failed].slice(-CONFIG.errorWindowSize);
  state.completedRequests += 1;
  if (!failed) {
    state.successfulRequests += 1;
    state.successfulLatencies = [...state.successfulLatencies, pending.measuredLatencyMs].slice(-50);
  }
  state.decisions = state.decisions.map((record) => record.requestId === pending.requestId ? { ...record, status: pending.status } : record);
  if (state.latestDecision?.requestId === pending.requestId) {
    state.latestDecision = { ...state.latestDecision, status: pending.status };
  }

  if (backend.breaker === "half_open") {
    backend.probeInFlight = false;
    if (failed) {
      openBreaker(backend, state.elapsedMs);
    } else {
      backend.probeSuccesses += 1;
      if (backend.probeSuccesses >= CONFIG.probesToClose) {
        backend.breaker = "closed";
        backend.consecutiveFailures = 0;
        backend.outcomes = [];
        backend.probeSuccesses = 0;
      }
    }
  } else if (backend.breaker === "closed") {
    backend.consecutiveFailures = failed ? backend.consecutiveFailures + 1 : 0;
    const fullWindow = backend.outcomes.length >= CONFIG.errorWindowSize;
    if (backend.consecutiveFailures >= CONFIG.failuresToOpen || (fullWindow && errorRate(backend) >= CONFIG.errorThreshold)) {
      openBreaker(backend, state.elapsedMs);
    }
  }
}

function healthCheck(state: SimulatorState): void {
  for (const backend of state.backends) {
    if (backend.mode === "down") {
      backend.healthFailures += 1;
      backend.healthSuccesses = 0;
      if (backend.healthFailures >= CONFIG.unhealthyAfter) backend.healthy = false;
    } else {
      backend.healthSuccesses += 1;
      backend.healthFailures = 0;
      if (!backend.healthy && backend.healthSuccesses >= CONFIG.healthyAfter) backend.healthy = true;
    }
  }
}

export function advanceSimulation(previous: SimulatorState, deltaMs: number): SimulatorState {
  const state: SimulatorState = {
    ...previous,
    backends: previous.backends.map((backend) => ({ ...backend, outcomes: [...backend.outcomes] })),
    pending: [...previous.pending],
    decisions: [...previous.decisions],
    successfulLatencies: [...previous.successfulLatencies],
  };
  state.elapsedMs += deltaMs;

  for (const backend of state.backends) {
    if (backend.breaker === "open" && state.elapsedMs >= backend.openUntil) {
      backend.breaker = "half_open";
      backend.probeInFlight = false;
      backend.probeSuccesses = 0;
    }
  }

  state.healthAccumulator += deltaMs;
  while (state.healthAccumulator >= CONFIG.healthIntervalMs) {
    state.healthAccumulator -= CONFIG.healthIntervalMs;
    healthCheck(state);
  }

  if (state.autoTraffic) {
    state.autoAccumulator += (deltaMs * 12) / 1_000;
    while (state.autoAccumulator >= 1) {
      state.autoAccumulator -= 1;
      spawnRequest(state);
    }
  }
  const burst = Math.min(state.queuedRequests, 3);
  state.queuedRequests -= burst;
  for (let index = 0; index < burst; index += 1) spawnRequest(state);

  const remaining: PendingRequest[] = [];
  for (const pending of state.pending) {
    if (pending.completesAt <= state.elapsedMs) completeRequest(state, pending);
    else remaining.push(pending);
  }
  state.pending = remaining;
  return state;
}

export function withPolicy(state: SimulatorState, policy: PolicyId): SimulatorState {
  return { ...state, policy };
}

export function withAutoTraffic(state: SimulatorState, autoTraffic: boolean): SimulatorState {
  return { ...state, autoTraffic };
}

export function enqueueBurst(state: SimulatorState): SimulatorState {
  return { ...state, queuedRequests: state.queuedRequests + 20 };
}

export function withBackendMode(state: SimulatorState, backendId: string, mode: BackendMode): SimulatorState {
  return {
    ...state,
    backends: state.backends.map((backend) => backend.id === backendId ? { ...backend, mode } : backend),
  };
}

export function resetSimulator(state: SimulatorState): SimulatorState {
  return createSimulator(state.policy);
}

export function backendErrorRate(backend: BackendState): number {
  return errorRate(backend);
}

export function backendTrafficShare(state: SimulatorState, backendId: string): number {
  const recent = state.decisions.slice(-100).filter((record) => record.backendId !== null);
  if (recent.length === 0) return 0;
  return recent.filter((record) => record.backendId === backendId).length / recent.length;
}

export function averageSuccessfulLatency(state: SimulatorState): number {
  if (state.successfulLatencies.length === 0) return 0;
  return state.successfulLatencies.reduce((sum, latency) => sum + latency, 0) / state.successfulLatencies.length;
}

export function backendStatus(backend: BackendState, elapsedMs: number): { label: string; tone: "ok" | "warn" | "bad" } {
  if (!backend.healthy) return { label: "Unhealthy", tone: "bad" };
  if (backend.breaker === "open") return { label: `Circuit open · ${Math.max(1, Math.ceil((backend.openUntil - elapsedMs) / 1_000))}s`, tone: "bad" };
  if (backend.breaker === "half_open") return { label: "Half-open · probing", tone: "warn" };
  return { label: "Healthy", tone: "ok" };
}
