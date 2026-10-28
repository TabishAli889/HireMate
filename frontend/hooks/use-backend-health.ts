"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { HealthResponse } from "@/types/api";

export type BackendStatus = "checking" | "online" | "offline";

/** Polls GET /health through the proxy and reports whether the API is reachable. */
export function useBackendHealth(intervalMs = 30_000) {
  const [status, setStatus] = useState<BackendStatus>("checking");
  const [data, setData] = useState<HealthResponse | null>(null);

  const refresh = useCallback(async (): Promise<boolean> => {
    try {
      const res = await apiFetch<HealthResponse>("/health");
      setData(res);
      setStatus("online");
      return true;
    } catch {
      setData(null);
      setStatus("offline");
      return false;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), intervalMs);
    return () => window.clearInterval(id);
  }, [refresh, intervalMs]);

  return { status, data, refresh };
}
