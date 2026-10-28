"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  CalendarClock,
  CircleCheck,
  FileUser,
  GraduationCap,
  History,
  SquareKanban,
  MessageSquareText,
  ScanSearch,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";
import { PipelineBars, ScoreHistory } from "@/components/features/dashboard/charts";
import { GettingStarted } from "@/components/features/getting-started";
import { Greeting } from "@/components/features/greeting";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch } from "@/lib/api";
import { DEADLINE_CLASS, STATUS_META, deadlineInfo } from "@/lib/applications";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ActivityItem, Dashboard } from "@/types/dashboard";

const DESCRIPTION = "Match honestly, tailor without inventing, and track every application in one place.";

function StatTile({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: ReactNode; detail: ReactNode }) {
  return (
    <Card className="flex flex-col gap-3 p-5">
      <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="size-4" aria-hidden />
        {label}
      </span>
      <span className="font-heading text-3xl font-bold tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{detail}</span>
    </Card>
  );
}

function Panel({ title, icon: Icon, action, children, className }: { title: string; icon: LucideIcon; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <Card className={cn("flex flex-col gap-4 p-5 sm:p-6", className)}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="inline-flex items-center gap-2 font-semibold">
          <Icon className="size-4 text-primary" aria-hidden />
          {title}
        </h2>
        {action}
      </div>
      {children}
    </Card>
  );
}

function PanelLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
      {children}
      <ArrowRight className="size-3.5" aria-hidden />
    </Link>
  );
}

function Quiet({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">{children}</p>;
}

const ACTIVITY_ICON: Record<string, LucideIcon> = {
  analyzed: ScanSearch,
  created: SquareKanban,
  status: CircleCheck,
  deadline: CalendarClock,
  notes: MessageSquareText,
  details: Briefcase,
};

function activityHref(item: ActivityItem): string {
  if (item.application_id !== null) return `/applications?open=${item.application_id}`;
  return item.job_id !== null ? `/analyze?job=${item.job_id}` : "/";
}

export function DashboardSkeleton() {
  return (
    <div role="status" aria-label="Loading your dashboard" className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    </div>
  );
}

/** Home page: headline numbers, the pipeline, deadlines, score history, skills to learn and recent activity. */
export function DashboardView() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await apiFetch<Dashboard>("/dashboard"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your dashboard.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const firstName = data?.profile_name.trim().split(/\s+/)[0] ?? "";
  const header = (
    <PageHeader
      title={<Greeting name={firstName || undefined} />}
      description={DESCRIPTION}
      actions={
        <Button asChild>
          <Link href="/analyze">
            <Sparkles aria-hidden />
            Analyze a job
          </Link>
        </Button>
      }
    />
  );

  if (error) {
    return (
      <>
        {header}
        <Card className="flex flex-col items-center gap-3 p-8 text-center">
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => void load()}>
            Try again
          </Button>
        </Card>
      </>
    );
  }

  if (data === null) {
    return (
      <>
        {header}
        <DashboardSkeleton />
      </>
    );
  }

  const { stats } = data;
  const isNew = stats.applications === 0 && stats.jobs_analyzed === 0;

  if (isNew) {
    return (
      <>
        {header}
        <GettingStarted />
      </>
    );
  }

  return (
    <>
      {header}
      <div className="flex flex-col gap-6">
        {!data.has_profile && (
          <Card role="note" className="flex flex-col gap-3 border-primary/30 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="inline-flex items-start gap-2 text-sm">
              <FileUser className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              Upload your resume so HireMate can score matches and tailor documents.
            </p>
            <Button size="sm" asChild>
              <Link href="/profile">Go to Profile</Link>
            </Button>
          </Card>
        )}

        <section aria-label="Your numbers" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile
            icon={SquareKanban}
            label="Applications"
            value={stats.applications}
            detail={`${stats.active} still in progress`}
          />
          <StatTile
            icon={Target}
            label="Interview rate"
            value={stats.interview_rate === null ? "—" : `${stats.interview_rate}%`}
            detail={stats.sent === 0 ? "Move a card to Applied to start tracking" : `${stats.interviews} of ${stats.sent} sent reached an interview`}
          />
          <StatTile
            icon={BarChart3}
            label="Average match"
            value={stats.average_match === null ? "—" : `${stats.average_match}%`}
            detail={`${stats.jobs_scored} of ${stats.jobs_analyzed} analyzed job${stats.jobs_analyzed === 1 ? "" : "s"} scored`}
          />
          <StatTile
            icon={CircleCheck}
            label="Offers"
            value={stats.offers}
            detail={`${stats.documents_ready} job${stats.documents_ready === 1 ? "" : "s"} with documents ready`}
          />
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Pipeline" icon={SquareKanban} action={<PanelLink href="/applications">Open board</PanelLink>}>
            {stats.applications === 0 ? (
              <Quiet>Save a job to your tracker to see your pipeline here.</Quiet>
            ) : (
              <PipelineBars stages={data.pipeline} />
            )}
          </Panel>

          <Panel title="Upcoming deadlines" icon={CalendarClock}>
            {data.deadlines.length === 0 ? (
              <Quiet>No deadlines in the next two weeks. Add one from a card on your board.</Quiet>
            ) : (
              <ul className="flex flex-col divide-y divide-border">
                {data.deadlines.map((item) => {
                  const info = deadlineInfo(item.deadline);
                  return (
                    <li key={item.application_id}>
                      <Link
                        href={`/applications?open=${item.application_id}`}
                        className="flex items-center gap-3 py-2.5 text-sm hover:text-primary"
                      >
                        <span className={cn("size-2 shrink-0 rounded-full", STATUS_META[item.status].dot)} aria-hidden />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium">{item.title}</span>
                          <span className="block truncate text-xs text-muted-foreground">
                            {[item.company, STATUS_META[item.status].label].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <span className={cn("shrink-0 rounded-md px-2 py-0.5 text-xs font-medium", DEADLINE_CLASS[info.tone])}>{info.text}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </Panel>

          <Panel title="Match scores" icon={BarChart3} action={<PanelLink href="/analyze">Analyze another</PanelLink>}>
            {data.score_history.length === 0 ? (
              <Quiet>Score a job against your profile to see your match history.</Quiet>
            ) : (
              <ScoreHistory points={data.score_history} />
            )}
          </Panel>

          <Panel title="Skills to learn next" icon={GraduationCap}>
            {data.skill_gaps.length === 0 ? (
              <Quiet>
                {stats.jobs_scored === 0 ? "Score a job to see which skills you're missing." : "No required skills missing across your scored jobs."}
              </Quiet>
            ) : (
              <>
                <p className="-mt-2 text-sm text-muted-foreground">
                  Required skills you don’t show yet, by how many of your {stats.jobs_scored} scored job{stats.jobs_scored === 1 ? "" : "s"} ask for them.
                </p>
                <ul className="flex flex-col gap-3">
                  {data.skill_gaps.map((gap) => (
                    <li key={gap.skill} className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_4.5rem] items-center gap-3 text-sm">
                      <span className="truncate font-medium">{gap.skill}</span>
                      <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
                        <span className="block h-full rounded-full bg-primary" style={{ width: `${(gap.jobs / Math.max(1, stats.jobs_scored)) * 100}%` }} />
                      </span>
                      <span className="text-right text-xs tabular-nums text-muted-foreground">
                        {gap.jobs} of {stats.jobs_scored}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Panel>
        </div>

        <Panel title="Recent activity" icon={History}>
          {data.activity.length === 0 ? (
            <Quiet>Nothing yet.</Quiet>
          ) : (
            <ol className="flex flex-col divide-y divide-border">
              {data.activity.map((item, index) => {
                const Icon = ACTIVITY_ICON[item.kind] ?? History;
                return (
                  <li key={`${item.kind}-${item.created_at}-${index}`}>
                    <Link href={activityHref(item)} className="flex items-center gap-3 py-2.5 text-sm hover:text-primary">
                      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
                        <Icon className="size-4" aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">{item.message}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {[item.title, item.company].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground">{formatRelative(item.created_at)}</span>
                    </Link>
                  </li>
                );
              })}
            </ol>
          )}
        </Panel>
      </div>
    </>
  );
}
