export interface Backend {
  id: string;
  url: string;
  health_state: "HEALTHY" | "UNHEALTHY";
  circuit_state: "closed" | "open" | "half_open";
  in_flight: number;
  routed_requests: number;
  ewma_latency_ms: number;
  error_rate: number;
  cpu_percent: number;
  last_check_at: string | null;
}
export interface CandidateScore {
  backend_id: string; score: number; in_flight: number;
  ewma_latency_ms: number; cpu_percent: number; error_rate: number;
}
export interface Decision {
  request_id: string; policy: string; chosen_backend_id: string;
  reason: string; candidates: CandidateScore[]; at: string;
}
export interface Behavior {
  latency_ms: number; jitter_ms: number; error_rate: number; cpu_percent: number; down: boolean;
}
export interface BenchmarkResult {
  requests: number; failures: number; error_rate: number; rps: number;
  p50_ms: number; p95_ms: number; p99_ms: number;
}
export interface BenchmarkReport {
  results: Record<string, BenchmarkResult>;
  conditions: Record<string, string | number>;
}
export interface DashboardSnapshot {
  backends: Backend[]; policy: string; decisions: Decision[];
  connected: boolean; error: string | null; refreshNow: () => Promise<void>;
}
