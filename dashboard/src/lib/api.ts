import type { Backend, Behavior, Decision } from "@/lib/types";

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl + path, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error("RouteMesh returned " + response.status);
  return response.json() as Promise<T>;
}

export const loadBackends = (): Promise<Backend[]> => request("/admin/backends");
export const loadPolicy = (): Promise<{ policy: string }> => request("/admin/policy");
export const loadDecisions = (): Promise<Decision[]> => request("/admin/decisions?limit=30");

export function changePolicy(policy: string): Promise<{ policy: string }> {
  return request("/admin/policy", { method: "PUT", body: JSON.stringify({ policy }) });
}

export function changeBehavior(id: string, behavior: Behavior): Promise<unknown> {
  return request("/admin/backends/" + encodeURIComponent(id) + "/behavior", {
    method: "POST",
    body: JSON.stringify(behavior),
  });
}
