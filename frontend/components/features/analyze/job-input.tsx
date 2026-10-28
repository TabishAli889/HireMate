"use client";

import type { KeyboardEvent } from "react";
import { ClipboardPaste, Link2, Loader2, Sparkles, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { SAMPLE_JOB_POSTING } from "@/lib/sample-job";
import { cn } from "@/lib/utils";
import type { AgentGoal } from "@/types/agent";

export type InputMode = "text" | "url";

export const MIN_POSTING_CHARS = 80;

export function isValidJobUrl(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

const GOALS: { id: AgentGoal; label: string; hint: string }[] = [
  { id: "analyze", label: "Full analysis", hint: "Requirements, match score and skill plan" },
  { id: "prepare", label: "Prepare application", hint: "Analysis, tailored bullets, cover letter, interview prep, saved to your board" },
  { id: "extract", label: "Requirements only", hint: "Just read and structure the posting" },
];

interface JobInputProps {
  goal: AgentGoal;
  onGoalChange: (goal: AgentGoal) => void;
  mode: InputMode;
  onModeChange: (mode: InputMode) => void;
  text: string;
  onTextChange: (text: string) => void;
  url: string;
  onUrlChange: (url: string) => void;
  onSubmit: () => void;
  busy: boolean;
}

/** Paste a posting or give a URL, then run the analysis. Ctrl/⌘+Enter submits. */
export function JobInput({ goal, onGoalChange, mode, onModeChange, text, onTextChange, url, onUrlChange, onSubmit, busy }: JobInputProps) {
  const trimmed = text.trim().length;
  const canSubmit = !busy && (mode === "text" ? trimmed >= MIN_POSTING_CHARS : isValidJobUrl(url));

  const submitOnShortcut = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSubmit) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <Card className="p-5 sm:p-6">
      <Tabs
        label="Job posting source"
        value={mode}
        onValueChange={(id) => onModeChange(id as InputMode)}
        items={[
          { id: "text", label: "Paste text", icon: ClipboardPaste },
          { id: "url", label: "Job URL", icon: Link2 },
        ]}
      >
        {mode === "text" ? (
          <div className="flex flex-col gap-2">
            <label htmlFor="job-text" className="sr-only">
              Job posting text
            </label>
            <Textarea
              id="job-text"
              rows={12}
              value={text}
              onChange={(e) => onTextChange(e.target.value)}
              onKeyDown={submitOnShortcut}
              disabled={busy}
              placeholder="Paste the full job description here: title, requirements, responsibilities…"
              className="min-h-[14rem] text-[15px]"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {trimmed} characters
                {trimmed > 0 && trimmed < MIN_POSTING_CHARS && ` · at least ${MIN_POSTING_CHARS} needed`}
              </span>
              <Button type="button" variant="ghost" size="sm" className="text-primary" onClick={() => onTextChange(SAMPLE_JOB_POSTING)} disabled={busy}>
                <Wand2 aria-hidden />
                Try a sample posting
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <label htmlFor="job-url" className="text-xs font-medium text-muted-foreground">
              Link to the job posting
            </label>
            <Input
              id="job-url"
              type="url"
              inputMode="url"
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && canSubmit) onSubmit();
              }}
              disabled={busy}
              placeholder="https://careers.company.com/jobs/ai-intern"
              className="h-12 text-[15px]"
            />
            <p className="text-xs text-muted-foreground">
              Works with most company career pages. Sites that need a login (like LinkedIn) can’t be read; paste the text instead.
            </p>
          </div>
        )}
      </Tabs>

      <div className="mt-5 flex flex-col gap-4 border-t border-border pt-5 lg:flex-row lg:items-end lg:justify-between">
        <fieldset className="min-w-0">
          <legend className="mb-2 text-xs font-medium text-muted-foreground">What should the agent do?</legend>
          <div role="radiogroup" aria-label="Agent goal" className="flex flex-col gap-2 sm:flex-row">
            {GOALS.map((option) => {
              const selected = option.id === goal;
              return (
                <button
                  key={option.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  disabled={busy}
                  onClick={() => onGoalChange(option.id)}
                  className={cn(
                    "flex flex-col rounded-xl border border-border px-3 py-2 text-left transition-colors hover:border-primary/40 disabled:opacity-60",
                    selected && "border-primary bg-accent ring-1 ring-primary",
                  )}
                >
                  <span className={cn("text-sm font-medium", selected && "text-accent-foreground")}>{option.label}</span>
                  <span className="text-xs text-muted-foreground">{option.hint}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
        <Button size="lg" onClick={onSubmit} disabled={!canSubmit} className="shrink-0">
          {busy ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />}
          {busy ? "Agent working…" : "Run agent"}
        </Button>
      </div>
    </Card>
  );
}
