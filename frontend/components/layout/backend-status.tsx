"use client";

import { useBackendHealth, type BackendStatus as Status } from "@/hooks/use-backend-health";
import { cn } from "@/lib/utils";

const STATUS_UI: Record<Status, { label: string; dot: string }> = {
  checking: { label: "Checking API…", dot: "bg-muted-foreground animate-pulse" },
  online: { label: "API online", dot: "bg-success" },
  offline: { label: "API offline", dot: "bg-warning" },
};

/** Small pill in the top bar showing whether the FastAPI backend is reachable. */
export function BackendStatus() {
  const { status } = useBackendHealth();
  const ui = STATUS_UI[status];

  return (
    <span
      role="status"
      aria-live="polite"
      className="hidden items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1.5 text-xs font-medium text-muted-foreground sm:inline-flex"
    >
      <span className={cn("size-2 rounded-full", ui.dot)} aria-hidden />
      {ui.label}
    </span>
  );
}
