"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, CheckCircle2, Circle, CircleAlert, Info, Loader2, Sparkles, Square, X, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AgentNotice } from "@/types/agent";

export type StepStatus = "pending" | "active" | "done" | "error";

export interface AgentStep {
  id: string;
  label: string;
  detail: string;
  status: StepStatus;
  /** Tool name the agent called, e.g. "score_match". */
  tool?: string;
}

function StepIcon({ status }: { status: StepStatus }) {
  const base = "grid size-8 shrink-0 place-items-center rounded-full";
  if (status === "done")
    return (
      <span className={cn(base, "bg-success-soft text-success")}>
        <CheckCircle2 className="size-5" aria-hidden />
      </span>
    );
  if (status === "error")
    return (
      <span className={cn(base, "bg-destructive/10 text-destructive")}>
        <XCircle className="size-5" aria-hidden />
      </span>
    );
  if (status === "active")
    return (
      <span className={cn(base, "bg-brand text-[hsl(var(--gradient-foreground))] shadow-glow")}>
        <Loader2 className="size-4 animate-spin" aria-hidden />
      </span>
    );
  return (
    <span className={cn(base, "bg-muted text-muted-foreground")}>
      <Circle className="size-3" aria-hidden />
    </span>
  );
}

const STATUS_TEXT: Record<StepStatus, string> = { pending: "Waiting", active: "In progress", done: "Done", error: "Failed" };

interface AgentProgressProps {
  steps: AgentStep[];
  running?: boolean;
  notices?: AgentNotice[];
  summary?: string | null;
  error?: string | null;
  onStop?: () => void;
  onDismiss?: () => void;
  title?: string;
}

/** Live timeline of the tools the agent calls, plus notices and the final summary. */
export function AgentProgress({ steps, running = false, notices = [], summary, error, onStop, onDismiss, title = "Agent progress" }: AgentProgressProps) {
  const thinking = running && !steps.some((s) => s.status === "active");

  return (
    <Card className="p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <Bot className="size-4" aria-hidden />
          {title}
        </h2>
        {running && onStop && (
          <Button variant="ghost" size="sm" onClick={onStop}>
            <Square className="fill-current" aria-hidden />
            Stop
          </Button>
        )}
        {!running && onDismiss && (
          <Button variant="ghost" size="icon" className="size-8" onClick={onDismiss} aria-label="Hide agent progress">
            <X aria-hidden />
          </Button>
        )}
      </div>

      <ol aria-live="polite" className="flex flex-col">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1 && !thinking;
          return (
            <motion.li
              key={step.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative flex gap-4 pb-5 last:pb-0"
            >
              {!isLast && (
                <span className="absolute left-4 top-9 h-[calc(100%-2.25rem)] w-px -translate-x-1/2 bg-border" aria-hidden>
                  <motion.span
                    className="block w-full bg-success"
                    initial={false}
                    animate={{ height: step.status === "done" ? "100%" : "0%" }}
                    transition={{ duration: 0.4 }}
                  />
                </span>
              )}
              <StepIcon status={step.status} />
              <div className="min-w-0 flex-1 pt-1">
                <p className={cn("flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium", step.status === "pending" && "text-muted-foreground")}>
                  {step.label}
                  {step.status === "active" && "…"}
                  {step.tool && (
                    <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] font-normal text-muted-foreground">{step.tool}</code>
                  )}
                  <span className="sr-only"> ({STATUS_TEXT[step.status]})</span>
                </p>
                <AnimatePresence initial={false}>
                  {step.detail && step.status !== "active" && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className={cn("mt-1 line-clamp-3 text-xs", step.status === "error" ? "text-destructive" : "text-muted-foreground")}
                    >
                      {step.detail}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>
            </motion.li>
          );
        })}
        {thinking && (
          <li className="flex gap-4">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground">
              <Sparkles className="size-4 animate-pulse" aria-hidden />
            </span>
            <p className="pt-1.5 text-sm text-muted-foreground">{steps.length === 0 ? "Agent is planning…" : "Choosing the next step…"}</p>
          </li>
        )}
      </ol>

      {notices.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          {notices.map((notice, i) => (
            <li key={i} className="flex items-start gap-2 rounded-xl bg-warning-soft px-3 py-2 text-xs text-warning">
              <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span>
                {notice.message}
                {notice.count > 1 && <span className="ml-1 font-medium">(retry {notice.count})</span>}
              </span>
            </li>
          ))}
        </ul>
      )}

      {summary && !running && (
        <p className="mt-4 flex items-start gap-2 rounded-xl bg-accent px-3 py-2.5 text-sm text-accent-foreground">
          <Sparkles className="mt-0.5 size-4 shrink-0" aria-hidden />
          {summary}
        </p>
      )}
      {error && !running && (
        <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {error}
        </p>
      )}
    </Card>
  );
}
