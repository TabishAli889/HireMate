"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Building2, FileUser, Info, MapPin, Plus } from "lucide-react";
import { toast } from "sonner";
import { AgentProgress } from "@/components/features/analyze/agent-progress";
import { JobInput, type InputMode } from "@/components/features/analyze/job-input";
import { RecentJobs } from "@/components/features/analyze/recent-jobs";
import { ResultsPanel } from "@/components/features/analyze/results-panel";
import { TrackerButton } from "@/components/features/applications/tracker-button";
import { EmptyState } from "@/components/features/empty-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgentRun, type RunOutcome } from "@/hooks/use-agent-run";
import { useProfile } from "@/hooks/use-profile";
import { ApiError, apiFetch } from "@/lib/api";
import type { AgentGoal } from "@/types/agent";
import type { Job } from "@/types/job";

/** What we ask the agent for. The agent decides which tools that needs. */
const REQUESTS: Record<AgentGoal, string> = {
  analyze: "Analyze this job: extract the requirements, score my match and plan my skill gaps.",
  extract: "Only extract the job requirements. Do not score my match.",
  prepare:
    "Prepare my application: extract the requirements, score my match, plan my skill gaps, tailor my resume bullets, write a cover letter, generate interview questions and save the job to my tracker.",
};
const RESCORE_REQUEST = "Re-score my match for this saved job and refresh my skill plan.";

export function AnalyzeSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="flex flex-col gap-6">
      <Skeleton className="h-80 rounded-2xl" />
      <Skeleton className="h-40 rounded-2xl" />
    </div>
  );
}

/** Analyze Job page: input → live agent progress → tabbed results. The open job lives in `?job=<id>`. */
export function AnalyzeWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state: profileState } = useProfile();

  const [goal, setGoal] = useState<AgentGoal>("analyze");
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [loadingJob, setLoadingJob] = useState(false);
  const [recentKey, setRecentKey] = useState(0);

  const jobRef = useRef<Job | null>(null);
  jobRef.current = job;

  const jobParam = searchParams.get("job");
  const paramId = jobParam && /^\d+$/.test(jobParam) ? Number(jobParam) : null;
  const paramRef = useRef(paramId);
  paramRef.current = paramId;

  // Every job update the agent streams lands here; the URL follows the job being worked on.
  const handleJob = useCallback(
    (updated: Job) => {
      setJob(updated);
      if (paramRef.current !== updated.id) router.replace(`/analyze?job=${updated.id}`, { scroll: false });
    },
    [router],
  );
  const agent = useAgentRun(handleJob);
  const running = agent.status === "running";

  // Keep the open job in sync with the URL (reload, back/forward, opening a recent analysis).
  useEffect(() => {
    if (paramId === null) {
      setJob(null);
      return;
    }
    if (jobRef.current?.id === paramId) return;
    let cancelled = false;
    setLoadingJob(true);
    apiFetch<Job>(`/jobs/${paramId}`)
      .then((loaded) => {
        if (!cancelled) setJob(loaded);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        toast.error(err instanceof ApiError ? err.message : "Couldn't open that analysis.");
        router.replace("/analyze");
      })
      .finally(() => {
        if (!cancelled) setLoadingJob(false);
      });
    return () => {
      cancelled = true;
    };
  }, [paramId, router]);

  const report = (outcome: RunOutcome) => {
    setRecentKey((k) => k + 1);
    if (outcome.status === "done") toast.success(outcome.summary ?? "Done");
    else if (outcome.status === "error") toast.error(outcome.error ?? "The agent hit a problem.");
    else toast.message("Stopped. Anything already finished is saved.");
  };

  const start = async () => {
    if (running) return;
    const request = REQUESTS[goal];
    const outcome = await agent.run(mode === "url" ? { request, url: url.trim() } : { request, text });
    if (outcome.failedTools.includes("scrape_job_url")) setMode("text");
    report(outcome);
  };

  const rescore = async (target: Job) => {
    if (running) return;
    report(await agent.run({ request: RESCORE_REQUEST, job_id: target.id }));
  };

  const runOnJob = async (target: Job, request: string) => {
    if (running) return;
    report(await agent.run({ request, job_id: target.id }));
  };

  const updateJob = useCallback((update: (current: Job) => Job) => setJob((prev) => (prev ? update(prev) : prev)), []);

  const startOver = () => {
    agent.reset();
    router.push("/analyze");
  };

  if (profileState.status === "loading") return <AnalyzeSkeleton />;

  if (profileState.status === "empty") {
    return (
      <EmptyState
        icon={FileUser}
        title="Add your resume first"
        description="Matching compares each job with your Profile Vault. Upload your resume once, then analyze as many jobs as you like."
        action={{ label: "Go to Profile", href: "/profile" }}
      />
    );
  }

  const profile = profileState.status === "ready" ? profileState.profile : null;
  const progress = agent.status !== "idle" && (
    <AgentProgress
      steps={agent.steps}
      running={running}
      notices={agent.notices}
      summary={agent.summary}
      error={agent.error}
      onStop={agent.stop}
      onDismiss={agent.reset}
    />
  );

  const demoNotice = profile?.is_demo && (
    <Card role="note" className="flex items-start gap-3 border-primary/30 p-4">
      <Info className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
      <p className="text-sm">
        <span className="font-semibold">You’re matching against the demo profile.</span>{" "}
        <span className="text-muted-foreground">
          For real results,{" "}
          <Link href="/profile" className="font-medium text-primary underline-offset-4 hover:underline">
            upload your resume
          </Link>
          .
        </span>
      </p>
    </Card>
  );

  if (loadingJob) return <AnalyzeSkeleton />;

  if (job) {
    return (
      <div className="flex flex-col gap-6">
        {demoNotice}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h2 className="truncate text-xl font-bold sm:text-2xl">{job.title || "Untitled role"}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              {job.company && (
                <span className="inline-flex items-center gap-1.5">
                  <Building2 className="size-4" aria-hidden />
                  {job.company}
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-4" aria-hidden />
                  {job.location}
                </span>
              )}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <TrackerButton job={job} onJobChange={updateJob} disabled={running} />
            <Button variant="outline" onClick={startOver} disabled={running}>
              <Plus aria-hidden />
              New analysis
            </Button>
          </div>
        </div>
        {progress}
        <ResultsPanel
          job={job}
          running={running}
          onScore={() => void rescore(job)}
          profileUpdatedAt={profile?.updated_at}
          onJobChange={updateJob}
          onRunAgent={(request) => void runOnJob(job, request)}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {demoNotice}
      <JobInput
        goal={goal}
        onGoalChange={setGoal}
        mode={mode}
        onModeChange={setMode}
        text={text}
        onTextChange={setText}
        url={url}
        onUrlChange={setUrl}
        onSubmit={() => void start()}
        busy={running}
      />
      {progress}
      {!running && <RecentJobs refreshKey={recentKey} onSelect={(id) => router.push(`/analyze?job=${id}`)} />}
    </div>
  );
}
