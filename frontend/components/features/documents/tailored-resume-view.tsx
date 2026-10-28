"use client";

import { useState } from "react";
import { CheckCheck, Download, FilePen, RefreshCw, ShieldCheck, Trophy } from "lucide-react";
import { toast } from "sonner";
import { BulletReview } from "@/components/features/documents/bullet-review";
import { GenerateCard, StaleNote, isStale, type DocumentViewProps } from "@/components/features/documents/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError, apiFetch } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BulletStatus, BulletSuggestion, Job, TailoringResult } from "@/types/job";

export const TAILOR_REQUEST = "Tailor my resume bullets for this saved job.";

function groupByContext(bullets: BulletSuggestion[]): [string, BulletSuggestion[]][] {
  const groups = new Map<string, BulletSuggestion[]>();
  for (const bullet of bullets) groups.set(bullet.context, [...(groups.get(bullet.context) ?? []), bullet]);
  return [...groups.entries()];
}

/** Tailored resume tab: before/after diff per bullet, accept/reject/edit, project ranking and PDF export. */
export function TailoredResumeView({ job, onJobChange, agentBusy, onRunAgent }: DocumentViewProps) {
  const [regenerating, setRegenerating] = useState(false);
  const tailoring = job.tailoring;

  if (!tailoring) {
    return (
      <GenerateCard
        icon={FilePen}
        title="Tailor your resume for this job"
        description="The agent rewrites your existing bullets in this job's language (no new facts or numbers), ranks your projects, and you approve every change."
        actionLabel="Tailor my bullets"
        onAction={() => onRunAgent(TAILOR_REQUEST)}
        busy={agentBusy}
        busyLabel="Agent working…"
      />
    );
  }

  const changed = tailoring.bullets.filter((b) => b.tailored.trim() !== b.original.trim());
  const guarded = tailoring.bullets.filter((b) => b.guard_note);
  const unchanged = tailoring.bullets.filter((b) => b.tailored.trim() === b.original.trim() && !b.guard_note);
  const accepted = changed.filter((b) => b.status === "accepted").length;
  const pending = changed.filter((b) => b.status === "pending");

  const setTailoring = (next: TailoringResult) => onJobChange((j: Job) => ({ ...j, tailoring: next }));

  const send = async (body: { decisions?: Record<string, BulletStatus>; edits?: Record<string, string> }, optimistic: TailoringResult) => {
    setTailoring(optimistic);
    try {
      setTailoring(await apiFetch<TailoringResult>(`/jobs/${job.id}/tailor`, { method: "PATCH", body: JSON.stringify(body) }));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't save that change.");
      setTailoring(tailoring);
    }
  };

  const decide = (ids: string[], status: BulletStatus) =>
    void send(
      { decisions: Object.fromEntries(ids.map((id) => [id, status])) },
      { ...tailoring, bullets: tailoring.bullets.map((b) => (ids.includes(b.id) ? { ...b, status } : b)) },
    );

  const saveEdit = (id: string, text: string) =>
    void send(
      { edits: { [id]: text } },
      { ...tailoring, bullets: tailoring.bullets.map((b) => (b.id === id ? { ...b, tailored: text, status: "accepted" as const, guard_note: "" } : b)) },
    );

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const result = await apiFetch<TailoringResult>(`/jobs/${job.id}/tailor`, { method: "POST", body: JSON.stringify({ regenerate: true }) });
      setTailoring(result);
      toast.success("Fresh suggestions ready");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't regenerate the suggestions.");
    } finally {
      setRegenerating(false);
    }
  };

  const busy = agentBusy || regenerating;

  return (
    <div className="flex flex-col gap-6">
      {isStale(job, tailoring.profile_fingerprint) && <StaleNote what="these suggestions" onRegenerate={() => void regenerate()} busy={busy} />}

      <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h2 className="font-semibold">Tailored for {job.title || "this job"}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {changed.length} of {tailoring.bullets.length} bullets rewritten · {accepted} accepted · {pending.length} to review · updated{" "}
            {formatRelative(tailoring.generated_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" onClick={() => void regenerate()} disabled={busy}>
            <RefreshCw className={cn(regenerating && "animate-spin")} aria-hidden />
            Regenerate
          </Button>
          <Button variant="outline" size="sm" onClick={() => decide(pending.map((b) => b.id), "accepted")} disabled={busy || pending.length === 0}>
            <CheckCheck aria-hidden />
            Accept all
          </Button>
          <Button size="sm" asChild>
            <a href={`/api/backend/jobs/${job.id}/tailor/pdf`} download>
              <Download aria-hidden />
              Export PDF
            </a>
          </Button>
        </div>
      </Card>

      {tailoring.projects.length > 0 && (
        <Card className="p-5 sm:p-6">
          <h3 className="inline-flex items-center gap-2 font-semibold">
            <Trophy className="size-4 text-primary" aria-hidden />
            Projects to highlight, in order
          </h3>
          <ol className="mt-3 flex flex-col gap-2">
            {tailoring.projects.map((project) => (
              <li key={project.name} className="flex items-start gap-3 text-sm">
                <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-accent text-xs font-semibold text-accent-foreground">
                  {project.rank}
                </span>
                <span>
                  <span className="font-medium">{project.name}</span>
                  {project.reason && <span className="text-muted-foreground"> · {project.reason}</span>}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {changed.length === 0 ? (
        <Card className="p-6 text-sm text-muted-foreground">No rewrites were needed: your bullets already fit this job well.</Card>
      ) : (
        groupByContext(changed).map(([context, bullets]) => (
          <section key={context} aria-label={context}>
            <h3 className="mb-3 text-sm font-semibold">{context}</h3>
            <ul className="flex flex-col gap-3">
              {bullets.map((bullet) => (
                <BulletReview
                  key={`${bullet.id}-${bullet.tailored}`}
                  bullet={bullet}
                  disabled={busy}
                  onDecide={(status) => decide([bullet.id], status)}
                  onSaveEdit={(text) => saveEdit(bullet.id, text)}
                />
              ))}
            </ul>
          </section>
        ))
      )}

      {guarded.length > 0 && (
        <Card className="p-5 sm:p-6">
          <h3 className="inline-flex items-center gap-2 font-semibold">
            <ShieldCheck className="size-4 text-success" aria-hidden />
            Honesty check kept {guarded.length} original{guarded.length === 1 ? "" : "s"}
          </h3>
          <ul className="mt-3 flex flex-col gap-3">
            {guarded.map((bullet) => (
              <li key={bullet.id} className="text-sm">
                <p>{bullet.original}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{bullet.guard_note}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {unchanged.length > 0 && (
        <details className="group rounded-2xl border border-border bg-card/40 p-4 text-sm">
          <summary className="cursor-pointer font-medium">
            {unchanged.length} bullet{unchanged.length === 1 ? "" : "s"} kept as-is
          </summary>
          <ul className="mt-3 flex flex-col gap-2 text-muted-foreground">
            {unchanged.map((bullet) => (
              <li key={bullet.id}>
                <Badge variant="outline" className="mr-2">
                  {bullet.context}
                </Badge>
                {bullet.original}
              </li>
            ))}
          </ul>
        </details>
      )}

      <p className="text-xs text-muted-foreground">
        The PDF uses accepted rewrites and your ranked project order. Everything else comes straight from your Profile Vault.
      </p>
    </div>
  );
}
