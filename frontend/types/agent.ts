/** Mirrors the events streamed by POST /agent/run (backend `app/services/agent`). */
import type { Job } from "@/types/job";

export type AgentGoal = "analyze" | "extract" | "prepare";

export interface AgentRunBody {
  request: string;
  text?: string;
  url?: string;
  job_id?: number;
  tone?: "professional" | "friendly" | "confident";
}

export interface AgentStepEvent {
  id: string;
  tool: string;
  label: string;
  status: "running" | "done" | "error";
  /** Tool observation when done, error message when failed. */
  detail: string;
}

export interface AgentDoneEvent {
  summary: string;
  job_id: number | null;
}

export type NoticeKind = "rate_limit" | "fallback" | "info";

export interface AgentNotice {
  kind: NoticeKind;
  message: string;
  /** How many times this notice repeated (rate-limit retries are merged into one line). */
  count: number;
}

export type AgentEventMap = {
  run: { request: string };
  step: AgentStepEvent;
  notice: { kind?: NoticeKind; message: string };
  job: Job;
  done: AgentDoneEvent;
  error: { message: string };
};
