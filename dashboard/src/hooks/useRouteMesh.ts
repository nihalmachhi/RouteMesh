"use client";
import { useCallback, useEffect, useState } from "react";
import { loadBackends, loadDecisions, loadPolicy } from "@/lib/api";
import type { DashboardSnapshot } from "@/lib/types";

const initial: DashboardSnapshot = {
  backends: [], policy: "unknown", decisions: [], connected: false, error: null,
  refreshNow: async () => undefined,
};

export function useRouteMesh(): DashboardSnapshot {
  const [state, setState] = useState(initial);
  const refresh = useCallback(async () => {
    try {
      const [backends, policy, decisions] = await Promise.all([
        loadBackends(), loadPolicy(), loadDecisions(),
      ]);
      setState((current) => ({
        ...current, backends, policy: policy.policy, decisions, error: null,
      }));
    } catch (error) {
      setState((current) => ({
        ...current, error: error instanceof Error ? error.message : "API unavailable",
      }));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 5000);
    const api = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
    const stream = new EventSource(api + "/admin/stream");
    stream.onopen = () => setState((current) => ({ ...current, connected: true }));
    stream.onmessage = () => void refresh();
    stream.onerror = () => setState((current) => ({ ...current, connected: false }));
    return () => {
      window.clearInterval(poll);
      stream.close();
    };
  }, [refresh]);

  return { ...state, refreshNow: refresh };
}
