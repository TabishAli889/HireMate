"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Eye, EyeOff, FolderGit2, MessagesSquare, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { GenerateCard, StaleNote, isStale } from "@/components/features/documents/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError, apiFetch } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InterviewPrep, InterviewQuestion, Job } from "@/types/job";

const CATEGORY: Record<InterviewQuestion["category"], { label: string; variant: "default" | "success" | "warning" | "muted" }> = {
  technical: { label: "Technical", variant: "default" },
  project: { label: "Your projects", variant: "success" },
  behavioral: { label: "Behavioral", variant: "warning" },
  role: { label: "Role & company", variant: "muted" },
};

interface InterviewPrepViewProps {
  job: Job;
  onJobChange: (update: (job: Job) => Job) => void;
  agentBusy?: boolean;
}

/** Eight likely questions; hints stay hidden until you've tried answering (practice mode). */
export function InterviewPrepView({ job, onJobChange, agentBusy = false }: InterviewPrepViewProps) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const prep = job.interview_prep;

  const generate = async (regenerate: boolean) => {
    setBusy(true);
    try {
      const result = await apiFetch<InterviewPrep>(`/jobs/${job.id}/interview-prep`, {
        method: "POST",
        body: JSON.stringify({ regenerate }),
      });
      onJobChange((j: Job) => ({ ...j, interview_prep: result }));
      setOpen(new Set());
      toast.success("Interview questions ready");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't prepare interview questions.");
    } finally {
      setBusy(false);
    }
  };

  if (!prep) {
    return (
      <GenerateCard
        icon={MessagesSquare}
        title="Practice for this interview"
        description="Eight likely questions for this exact job, each with a hint that points to your own projects. For skills you're missing, hints suggest an honest answer."
        actionLabel="Generate questions"
        onAction={() => void generate(false)}
        busy={busy || agentBusy}
        busyLabel="Preparing questions…"
      />
    );
  }

  const allOpen = open.size === prep.questions.length;
  const toggle = (index: number) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });

  return (
    <div className="flex flex-col gap-4">
      {isStale(job, prep.profile_fingerprint) && <StaleNote what="these questions" onRegenerate={() => void generate(true)} busy={busy} />}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {prep.questions.length} questions · try answering out loud before opening a hint · {formatRelative(prep.generated_at)}
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => setOpen(allOpen ? new Set() : new Set(prep.questions.map((_, i) => i)))}>
            {allOpen ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
            {allOpen ? "Hide all hints" : "Show all hints"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => void generate(true)} disabled={busy || agentBusy}>
            <RefreshCw className={cn(busy && "animate-spin")} aria-hidden />
            New questions
          </Button>
        </div>
      </div>

      <ol className="flex flex-col gap-3">
        {prep.questions.map((question, index) => {
          const isOpen = open.has(index);
          const category = CATEGORY[question.category];
          return (
            <li key={`${index}-${question.question}`}>
              <Card className="p-5">
                <div className="flex items-start gap-4">
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-accent font-heading text-sm font-bold text-accent-foreground">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge variant={category.variant}>{category.label}</Badge>
                      {question.project && (
                        <Badge variant="outline">
                          <FolderGit2 className="size-3.5" aria-hidden />
                          {question.project}
                        </Badge>
                      )}
                    </div>
                    <p className="font-medium leading-relaxed">{question.question}</p>
                    <button
                      type="button"
                      onClick={() => toggle(index)}
                      aria-expanded={isOpen}
                      className="mt-3 inline-flex items-center gap-1 rounded-md text-sm font-medium text-primary"
                    >
                      <ChevronDown className={cn("size-4 transition-transform", isOpen && "rotate-180")} aria-hidden />
                      {isOpen ? "Hide hint" : "Show hint"}
                    </button>
                    <AnimatePresence initial={false}>
                      {isOpen && (
                        <motion.p
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden text-sm leading-relaxed text-muted-foreground"
                        >
                          <span className="block pt-2">{question.hint}</span>
                        </motion.p>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </Card>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
