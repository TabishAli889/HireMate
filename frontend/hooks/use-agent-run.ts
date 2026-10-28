"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentStep } from "@/components/features/analyze/agent-progress";
import { ApiError } from "@/lib/api";
import { postEventStream, type SSEMessage } from "@/lib/sse";
import type { AgentEventMap, AgentNotice, AgentRunBody } from "@/types/agent";
import type { Job } from "@/types/job";

export type RunStatus = "idle" | "running" | "done" | "error" | "stopped";

export interface RunOutcome {
  status: "done" | "error" | "stopped";
  summary?: string;
  error?: string;
  /** Tools whose step failed (e.g. "scrape_job_url"). */
  failedTools: string[];
  jobId: number | null;
}

function toStep(event: AgentEventMap["step"]): AgentStep {
  return {
    id: event.id,
    tool: event.tool,
    label: event.label,
    detail: event.detail,
    status: event.status === "running" ? "active" : event.status,
  };
}

/** Repeated rate-limit waits update one line instead of stacking up. */
function addNotice(notices: AgentNotice[], incoming: AgentEventMap["notice"]): AgentNotice[] {
  const kind = incoming.kind ?? "info";
  const last = notices[notices.length - 1];
  if (kind === "rate_limit" && last?.kind === "rate_limit") {
    return [...notices.slice(0, -1), { kind, message: incoming.message, count: last.count + 1 }];
  }
  return [...notices, { kind, message: incoming.message, count: 1 }];
}

function upsertStep(steps: AgentStep[], step: AgentStep): AgentStep[] {
  const index = steps.findIndex((s) => s.id === step.id);
  if (index === -1) return [...steps, step];
  return steps.map((s, i) => (i === index ? step : s));
}

/** Runs POST /agent/run and turns its SSE events into UI state. `onJob` receives every job update. */
export function useAgentRun(onJob: (job: Job) => void) {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [notices, setNotices] = useState<AgentNotice[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onJobRef = useRef(onJob);

  useEffect(() => {
    onJobRef.current = onJob;
  });

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(async (body: AgentRunBody): Promise<RunOutcome> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("running");
    setSteps([]);
    setNotices([]);
    setSummary(null);
    setError(null);

    const failedTools: string[] = [];
    let lastJobId: number | null = null;
    let outcome: RunOutcome | null = null;

    const handle = ({ event, data }: SSEMessage) => {
      if (event === "step") {
        const step = data as AgentEventMap["step"];
        if (step.status === "error") failedTools.push(step.tool);
        setSteps((prev) => upsertStep(prev, toStep(step)));
      } else if (event === "notice") {
        const notice = data as AgentEventMap["notice"];
        setNotices((prev) => addNotice(prev, notice));
      } else if (event === "job") {
        const job = data as AgentEventMap["job"];
        lastJobId = job.id;
        onJobRef.current(job);
      } else if (event === "done") {
        const done = data as AgentEventMap["done"];
        outcome = { status: "done", summary: done.summary, failedTools, jobId: done.job_id };
        setSummary(done.summary);
        setStatus("done");
      } else if (event === "error") {
        const { message } = data as AgentEventMap["error"];
        outcome = { status: "error", error: message, failedTools, jobId: lastJobId };
        setError(message);
        setStatus("error");
      }
    };

    try {
      await postEventStream("/agent/run", body, handle, controller.signal);
    } catch (err) {
      if (controller.signal.aborted) {
        outcome = { status: "stopped", failedTools, jobId: lastJobId };
        setStatus("stopped");
      } else {
        const message = err instanceof ApiError ? err.message : "The agent could not start. Please try again.";
        outcome = { status: "error", error: message, failedTools, jobId: lastJobId };
        setError(message);
        setStatus("error");
      }
    }

    if (outcome === null) {
      const message = "The agent stopped unexpectedly. Please try again.";
      outcome = { status: "error", error: message, failedTools, jobId: lastJobId };
      setError(message);
      setStatus("error");
    }
    if (outcome.status !== "done") {
      // Anything still spinning didn't finish.
      setSteps((prev) => prev.map((s) => (s.status === "active" ? { ...s, status: "error", detail: "Stopped before finishing." } : s)));
    }
    if (abortRef.current === controller) abortRef.current = null;
    return outcome;
  }, []);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
    setSteps([]);
    setNotices([]);
    setSummary(null);
    setError(null);
  }, []);

  return { status, steps, notices, summary, error, run, stop, reset };
}
