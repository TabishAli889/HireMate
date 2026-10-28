"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiFetch } from "@/lib/api";
import type { Profile, ProfileData } from "@/types/profile";

export type ProfileState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "ready"; profile: Profile };

/** Loads GET /profile and exposes save (PUT) and replace (after upload). */
export function useProfile() {
  const [state, setState] = useState<ProfileState>({ status: "loading" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      setState({ status: "ready", profile: await apiFetch<Profile>("/profile") });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setState({ status: "empty" });
      else setState({ status: "error", message: err instanceof Error ? err.message : "Could not load your profile." });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async (data: ProfileData): Promise<Profile> => {
    const profile = await apiFetch<Profile>("/profile", { method: "PUT", body: JSON.stringify(data) });
    setState({ status: "ready", profile });
    return profile;
  }, []);

  const replace = useCallback((profile: Profile) => setState({ status: "ready", profile }), []);

  return { state, reload: load, save, replace };
}
