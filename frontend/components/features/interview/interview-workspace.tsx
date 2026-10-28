"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Briefcase, Check, MessagesSquare } from "lucide-react";
import { toast } from "sonner";
import { InterviewPrepView } from "@/components/features/documents/interview-prep-view";
import { EmptyState } from "@/components/features/empty-state";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Job, JobSummary } from "@/types/job";

export function InterviewSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <Skeleton className="h-64 rounded-2xl" />
      <Skeleton className="h-96 rounded-2xl" />
    </div>
  );
}

/** Pick a saved job on the left, practise its questions on the right. Selection lives in `?job=<id>`. */
export function InterviewWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [job, setJob] = useState<Job | null>(null);

  const param = searchParams.get("job");
  const requested = param && /^\d+$/.test(param) ? Number(param) : null;

  useEffect(() => {
    apiFetch<JobSummary[]>("/jobs?limit=50")
      .then(setJobs)
      .catch((err: unknown) => {
        toast.error(err instanceof ApiError ? err.message : "Couldn't load your jobs.");
        setJobs([]);
      });
  }, []);

  // Requested job, else the most recent one with questions, else the most recent job.
  const selectedId =
    (jobs?.find((j) => j.id === requested) ?? jobs?.find((j) => j.has_interview_prep) ?? jobs?.[0])?.id ?? null;

  useEffect(() => {
    if (selectedId === null) return;
    let cancelled = false;
    setJob(null);
    apiFetch<Job>(`/jobs/${selectedId}`)
      .then((loaded) => {
        if (!cancelled) setJob(loaded);
      })
      .catch((err: unknown) => {
        if (!cancelled) toast.error(err instanceof ApiError ? err.message : "Couldn't open that job.");
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  if (jobs === null) return <InterviewSkeleton />;

  if (jobs.length === 0) {
    return (
      <EmptyState
        icon={MessagesSquare}
        title="Nothing to prep yet"
        description="Analyze a job first. HireMate then writes eight likely questions for it, with hints drawn from your own projects."
        action={{ label: "Analyze a job", href: "/analyze" }}
      />
    );
  }

  const updateJob = (update: (current: Job) => Job) => {
    setJob((prev) => {
      if (!prev) return prev;
      const next = update(prev);
      if (next.interview_prep && !prev.interview_prep) {
        setJobs((list) => list?.map((j) => (j.id === next.id ? { ...j, has_interview_prep: true } : j)) ?? list);
      }
      return next;
    });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <Card className="h-fit p-2">
        <h2 className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Your jobs</h2>
        <ul className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
          {jobs.map((item) => {
            const active = item.id === selectedId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-current={active ? "true" : undefined}
                  onClick={() => router.replace(`/interview-prep?job=${item.id}`, { scroll: false })}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-muted",
                    active && "bg-accent text-accent-foreground hover:bg-accent",
                  )}
                >
                  <Briefcase className="size-4 shrink-0" aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{item.title || "Untitled role"}</span>
                    <span className="block truncate text-xs text-muted-foreground">{item.company || "Unknown company"}</span>
                  </span>
                  {item.has_interview_prep && <Check className="size-4 shrink-0 text-success" aria-label="Questions ready" />}
                </button>
              </li>
            );
          })}
        </ul>
      </Card>

      <section aria-label="Interview questions" className="min-w-0">
        {job ? (
          <>
            <h2 className="mb-4 truncate text-lg font-semibold">
              {job.title || "Untitled role"}
              {job.company && <span className="font-normal text-muted-foreground"> · {job.company}</span>}
            </h2>
            <InterviewPrepView job={job} onJobChange={updateJob} />
          </>
        ) : (
          <Skeleton className="h-96 rounded-2xl" />
        )}
      </section>
    </div>
  );
}
