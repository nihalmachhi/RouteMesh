import { useEffect, useRef, useState } from "react";
import {
  advanceSimulation,
  createSimulator,
  enqueueBurst,
  resetSimulator,
  withAutoTraffic,
  withBackendMode,
  withPolicy,
  type BackendMode,
  type PolicyId,
  type SimulatorState,
} from "./model";

function createInitialState(): SimulatorState {
  let state = createSimulator();
  for (let step = 0; step < 120; step += 1) state = advanceSimulation(state, 50);
  return state;
}

export function useSimulator() {
  const stateRef = useRef<SimulatorState | null>(null);
  if (!stateRef.current) stateRef.current = createInitialState();
  const [state, setState] = useState(stateRef.current);

  function update(transform: (current: SimulatorState) => SimulatorState) {
    const next = transform(stateRef.current!);
    stateRef.current = next;
    setState(next);
  }

  useEffect(() => {
    let ticks = 0;
    const timer = window.setInterval(() => {
      if (document.hidden) return;
      stateRef.current = advanceSimulation(stateRef.current!, 50);
      ticks += 1;
      if (ticks % 4 === 0) setState(stateRef.current);
    }, 50);
    return () => window.clearInterval(timer);
  }, []);

  return {
    state,
    choosePolicy: (policy: PolicyId) => update((current) => withPolicy(current, policy)),
    toggleAutoTraffic: () => update((current) => withAutoTraffic(current, !current.autoTraffic)),
    setAutoTraffic: (enabled: boolean) => update((current) => withAutoTraffic(current, enabled)),
    sendBurst: () => update(enqueueBurst),
    setBackendMode: (id: string, mode: BackendMode) => update((current) => withBackendMode(current, id, mode)),
    reset: () => update(resetSimulator),
  };
}
