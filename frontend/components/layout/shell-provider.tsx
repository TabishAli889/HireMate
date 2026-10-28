"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { useHotkey } from "@/hooks/use-hotkey";

const SIDEBAR_STORAGE_KEY = "hiremate:sidebar-collapsed";

interface ShellContextValue {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  paletteOpen: boolean;
  setPaletteOpen: Dispatch<SetStateAction<boolean>>;
}

const ShellContext = createContext<ShellContextValue | null>(null);

/** Holds layout UI state (sidebar collapse, command palette) and its keyboard shortcuts. */
export function ShellProvider({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    try {
      setSidebarCollapsed(window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1");
    } catch {
      // Storage blocked (private mode): fall back to expanded.
    }
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // Non-critical preference; ignore storage errors.
      }
      return next;
    });
  }, []);

  useHotkey("k", () => setPaletteOpen((open) => !open));
  useHotkey("b", toggleSidebar, { allowInInputs: false });

  const value = useMemo(
    () => ({ sidebarCollapsed, toggleSidebar, paletteOpen, setPaletteOpen }),
    [sidebarCollapsed, toggleSidebar, paletteOpen],
  );

  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>;
}

export function useShell(): ShellContextValue {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell must be used inside <ShellProvider>");
  return ctx;
}
