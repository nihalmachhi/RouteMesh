import { describe, expect, it } from "vitest";
import fixture from "./__fixtures__/policy-decisions.json";
import {
  NoHealthyBackendError,
  runSimulation,
  selectBackend,
  type BackendSignal,
  type PolicyName,
} from "./engine";

const policies: PolicyName[] = ["round_robin", "least_connections", "latency_aware"];
const backends = fixture.backends as BackendSignal[];

describe("RouteMesh policy parity fixture", () => {
  it.each(policies)("matches the Python %s decision", (policy) => {
    const expected = fixture.decisions[policy];
    const decision = selectBackend(
      policy,
      backends,
      fixture.request_id,
      fixture.rotation,
      fixture.weights,
    );

    expect(decision.chosen_backend_id).toBe(expected.chosen_backend_id);
    expect(decision.reason).toBe(expected.reason);
    expect(
      decision.candidates.map((candidate) => ({
        backend_id: candidate.backend_id,
        score: Math.round(candidate.score * 1e9) / 1e9,
        in_flight: candidate.in_flight,
      })),
    ).toEqual(expected.candidates);
  });
});

describe("selection boundaries and local load simulation", () => {
  it("filters unhealthy and open-circuit candidates before policy selection", () => {
    const candidates = [
      ...backends,
      { ...backends[0]!, backend_id: "backend-down", healthy: false },
      { ...backends[0]!, backend_id: "backend-open", circuit_state: "open" as const },
    ];
    const decision = selectBackend("round_robin", candidates, "req-001", 0);
    expect(decision.candidates.map((candidate) => candidate.backend_id)).toEqual([
      "backend-a",
      "backend-b",
      "backend-c",
    ]);
  });

  it("raises a clear error when every backend is ineligible", () => {
    expect(() =>
      selectBackend(
        "least_connections",
        backends.map((backend) => ({ ...backend, healthy: false })),
        "req-001",
        0,
      ),
    ).toThrow(NoHealthyBackendError);
  });

  it("is deterministic for the same seeded synthetic workload", () => {
    const input = {
      policy: "latency_aware" as const,
      backends,
      requestCount: 40,
      arrivalRate: 30,
      seed: 2701,
    };
    expect(runSimulation(input)).toEqual(runSimulation(input));
  });

  it("keeps backend shares bounded by total synthetic traffic", () => {
    const result = runSimulation({
      policy: "round_robin",
      backends,
      requestCount: 30,
      arrivalRate: 25,
      seed: 101,
    });
    expect(result.total).toBe(30);
    expect(result.shares.reduce((total, share) => total + share.count, 0)).toBeLessThanOrEqual(30);
    expect(result.shares.some((share) => share.count > 0)).toBe(true);
    expect(result.feed.length).toBeLessThanOrEqual(6);
  });
});