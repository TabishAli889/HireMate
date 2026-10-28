"use client";

import type { ReactNode } from "react";
import { Info, Loader2, RefreshCw, Sparkles, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { Job } from "@/types/job";

/** Props every document tab shares. `onJobChange` takes an updater so concurrent edits don't clobber each other. */
export interface DocumentViewProps {
  job: Job;
  onJobChange: (update: (job: Job) => Job) => void;
  /** The agent is running on this job (disable actions that would conflict). */
  agentBusy: boolean;
  /** Ask the agent to do something on this job, e.g. "Tailor my resume bullets…". */
  onRunAgent: (request: string) => void;
}

interface GenerateCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
  busy: boolean;
  busyLabel?: string;
  children?: ReactNode;
}

/** Empty state for a document that hasn't been generated yet. */
export function GenerateCard({ icon: Icon, title, description, actionLabel, onAction, busy, busyLabel, children }: GenerateCardProps) {
  return (
    <Card className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="grid size-12 place-items-center rounded-2xl bg-accent text-accent-foreground">
        <Icon className="size-6" aria-hidden />
      </span>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      {children}
      <Button onClick={onAction} disabled={busy} className="mt-1">
        {busy ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />}
        {busy ? busyLabel ?? "Working…" : actionLabel}
      </Button>
      {busy && <Progress value={null} label={busyLabel ?? "Working"} className="mt-2 max-w-xs" />}
    </Card>
  );
}

/** "Your profile changed since this was written" banner with a regenerate action. */
export function StaleNote({ what, onRegenerate, busy }: { what: string; onRegenerate: () => void; busy: boolean }) {
  return (
    <Card role="note" className="flex flex-col gap-3 border-warning/40 p-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="flex items-start gap-2 text-sm">
        <Info className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
        Your profile changed after {what} {what.endsWith("s") ? "were" : "was"} written.
      </p>
      <Button variant="outline" size="sm" onClick={onRegenerate} disabled={busy}>
        <RefreshCw className={cn(busy && "animate-spin")} aria-hidden />
        Regenerate
      </Button>
    </Card>
  );
}

/** True when a document was written for a different profile than the current match. */
export function isStale(job: Job, fingerprint: string | undefined): boolean {
  return Boolean(job.match?.profile_fingerprint && fingerprint && job.match.profile_fingerprint !== fingerprint);
}
