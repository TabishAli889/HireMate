"use client";

import { useState, type ReactNode } from "react";
import { FilePen, FileText, Gauge, ListChecks, Mail, MessagesSquare, Sparkles } from "lucide-react";
import { JobDetailsView } from "@/components/features/analyze/job-details-view";
import { MatchView } from "@/components/features/analyze/match-view";
import { SkillPlanView } from "@/components/features/analyze/skill-plan-view";
import { CoverLetterView } from "@/components/features/documents/cover-letter-view";
import { InterviewPrepView } from "@/components/features/documents/interview-prep-view";
import { TailoredResumeView } from "@/components/features/documents/tailored-resume-view";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import type { Job, MatchResult } from "@/types/job";

type TabId = "match" | "plan" | "resume" | "letter" | "interview" | "details";

interface ResultsPanelProps {
  job: Job;
  /** The agent is working on this job right now. */
  running: boolean;
  onScore: () => void;
  profileUpdatedAt?: string;
  onJobChange: (update: (job: Job) => Job) => void;
  onRunAgent: (request: string) => void;
}

const dot = <span className="size-1.5 rounded-full bg-success" aria-label="ready" />;

function NotScored({ onScore, running }: { onScore: () => void; running: boolean }) {
  return (
    <Card className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="grid size-12 place-items-center rounded-2xl bg-accent text-accent-foreground">
        <Gauge className="size-6" aria-hidden />
      </span>
      <h2 className="text-lg font-semibold">Not scored yet</h2>
      <p className="max-w-sm text-sm text-muted-foreground">Ask the agent to compare this job with your Profile Vault and plan your skill gaps.</p>
      <Button onClick={onScore} disabled={running}>
        <Sparkles aria-hidden />
        Score my match
      </Button>
    </Card>
  );
}

function PendingResults() {
  return (
    <div role="status" aria-label="Waiting for the agent" className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
      <Skeleton className="h-80 rounded-2xl" />
      <div className="flex flex-col gap-6">
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-28 rounded-2xl" />
        <Skeleton className="h-28 rounded-2xl" />
      </div>
    </div>
  );
}

/** Tabbed results for one analyzed job; sections fill in as the agent's tools finish. */
export function ResultsPanel({ job, running, onScore, profileUpdatedAt, onJobChange, onRunAgent }: ResultsPanelProps) {
  const docProps = { job, onJobChange, agentBusy: running, onRunAgent };
  const [tab, setTab] = useState<TabId>("match");
  const { match } = job;

  const scoredContent = (render: (result: MatchResult) => ReactNode) => {
    if (match) return render(match);
    if (running) return <PendingResults />;
    return <NotScored onScore={onScore} running={running} />;
  };

  const planPending = (result: MatchResult) =>
    running && result.gap_plan.length === 0 && result.missing_required.length + result.missing_nice.length > 0;

  return (
    <Tabs
      label="Analysis results"
      value={tab}
      onValueChange={(id) => setTab(id as TabId)}
      items={[
        { id: "match", label: "Match", icon: Gauge },
        {
          id: "plan",
          label: "Skill plan",
          icon: ListChecks,
          badge:
            match && match.gap_plan.length > 0 ? (
              <span className="rounded-md bg-accent px-1.5 text-xs text-accent-foreground">{match.gap_plan.length}</span>
            ) : undefined,
        },
        { id: "resume", label: "Resume", icon: FilePen, badge: job.tailoring ? dot : undefined },
        { id: "letter", label: "Cover letter", icon: Mail, badge: Object.keys(job.cover_letters).length > 0 ? dot : undefined },
        { id: "interview", label: "Interview", icon: MessagesSquare, badge: job.interview_prep ? dot : undefined },
        { id: "details", label: "Job details", icon: FileText },
      ]}
    >
      {tab === "match" &&
        scoredContent((result) => <MatchView match={result} onRescore={onScore} rescoring={running} profileUpdatedAt={profileUpdatedAt} />)}
      {tab === "plan" &&
        scoredContent((result) =>
          planPending(result) ? (
            <div role="status" aria-label="Writing your skill plan" className="flex flex-col gap-4">
              <Skeleton className="h-36 rounded-2xl" />
              <Skeleton className="h-36 rounded-2xl" />
            </div>
          ) : (
            <SkillPlanView match={result} onRescore={onScore} rescoring={running} />
          ),
        )}
      {tab === "resume" && scoredContent(() => <TailoredResumeView {...docProps} />)}
      {tab === "letter" && scoredContent(() => <CoverLetterView {...docProps} />)}
      {tab === "interview" && scoredContent(() => <InterviewPrepView {...docProps} />)}
      {tab === "details" && <JobDetailsView job={job} />}
    </Tabs>
  );
}
