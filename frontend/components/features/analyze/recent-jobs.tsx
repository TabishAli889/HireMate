"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronRight, History } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { STATUS_META } from "@/lib/applications";
import { formatRelative, scoreBand } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { JobSummary } from "@/types/job";

const TONE_TO_BADGE = { success: "success", primary: "default", warning: "warning" } as const;

interface RecentJobsProps {
  /** Change this number to refetch (e.g. after a new analysis). */
  refreshKey: number;
  onSelect: (id: number) => void;
}

/** Previously analyzed jobs; click one to reopen its results. */
export function RecentJobs({ refreshKey, onSelect }: RecentJobsProps) {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setFailed(false);
    try {
      setJobs(await apiFetch<JobSummary[]>("/jobs?limit=8"));
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  if (failed) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn’t load recent analyses.{" "}
        <Button variant="ghost" size="sm" className="text-primary" onClick={() => void load()}>
          Retry
        </Button>
      </p>
    );
  }

  if (jobs === null) {
    return (
      <div role="status" aria-label="Loading recent analyses" className="flex flex-col gap-2">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-16 rounded-2xl" />
        <Skeleton className="h-16 rounded-2xl" />
      </div>
    );
  }

  if (jobs.length === 0) return null;

  return (
    <section aria-labelledby="recent-jobs-heading">
      <h2 id="recent-jobs-heading" className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground">
        <History className="size-4" aria-hidden />
        Recent analyses
      </h2>
      <Card className="divide-y divide-border overflow-hidden">
        {jobs.map((job) => {
          const band = job.match_score !== null ? scoreBand(job.match_score) : null;
          return (
            <button
              key={job.id}
              type="button"
              onClick={() => onSelect(job.id)}
              className="flex w-full items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-muted/60 focus-visible:bg-muted/60 sm:px-5"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{job.title || "Untitled role"}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {[job.company, formatRelative(job.created_at)].filter(Boolean).join(" · ")}
                </p>
              </div>
              {job.application_status && (
                <span
                  className={cn(
                    "hidden shrink-0 rounded-md px-1.5 py-0.5 text-xs font-medium sm:inline",
                    STATUS_META[job.application_status].chip,
                  )}
                >
                  {STATUS_META[job.application_status].label}
                </span>
              )}
              {band && job.match_score !== null ? (
                <Badge variant={TONE_TO_BADGE[band.tone]} className="tabular-nums">
                  {job.match_score}
                </Badge>
              ) : (
                <Badge variant="muted">Not scored</Badge>
              )}
              <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            </button>
          );
        })}
      </Card>
    </section>
  );
}
