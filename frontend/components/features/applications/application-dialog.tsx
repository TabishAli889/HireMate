"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, Gauge, History, MessagesSquare, Save, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiFetch } from "@/lib/api";
import { STATUSES, deadlineInfo } from "@/lib/applications";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Application, ApplicationStatus, ApplicationUpdateBody } from "@/types/application";

type Draft = Required<ApplicationUpdateBody>;

function toDraft(card: Application): Draft {
  return { title: card.title, company: card.company, link: card.link, notes: card.notes, deadline: card.deadline };
}

interface ApplicationDialogProps {
  /** Render with `key={card.id}` so the form resets when another card opens. */
  card: Application;
  onClose: () => void;
  onSaved: (card: Application) => void;
  onMove: (id: number, status: ApplicationStatus, position: number) => void;
  onDeleted: (id: number) => void;
}

/** Everything about one application: status, details, deadline, notes and its timeline. */
export function ApplicationDialog({ card, onClose, onSaved, onMove, onDeleted }: ApplicationDialogProps) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(card));
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (!confirmDelete) return;
    const id = window.setTimeout(() => setConfirmDelete(false), 4000);
    return () => window.clearTimeout(id);
  }, [confirmDelete]);

  const original = toDraft(card);
  const changes = Object.fromEntries(
    (Object.keys(draft) as (keyof Draft)[]).filter((key) => draft[key] !== original[key]).map((key) => [key, draft[key]]),
  ) as ApplicationUpdateBody;
  const dirty = Object.keys(changes).length > 0;
  const linkInvalid = draft.link.trim() !== "" && !/^https?:\/\//i.test(draft.link.trim());
  const deadline = card.deadline ? deadlineInfo(card.deadline) : null;
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }));

  const save = async () => {
    if (!draft.title.trim()) {
      toast.error("Give the role a title.");
      return;
    }
    setSaving(true);
    try {
      const saved = await apiFetch<Application>(`/applications/${card.id}`, { method: "PATCH", body: JSON.stringify(changes) });
      onSaved(saved);
      setDraft(toDraft(saved));
      toast.success("Saved");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't save your changes.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    try {
      await apiFetch<void>(`/applications/${card.id}`, { method: "DELETE" });
      onDeleted(card.id);
      toast.success("Removed from your board");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't remove it.");
    }
  };

  const close = () => {
    if (dirty && !window.confirm("Discard your unsaved changes?")) return;
    onClose();
  };

  return (
    <Dialog open onOpenChange={(open) => !open && close()}>
      <DialogContent className="top-[4%] max-h-[92vh] max-w-2xl overflow-y-auto p-0">
        <div className="flex flex-col gap-6 p-5 sm:p-6">
          <div className="pr-8">
            <DialogTitle className="text-lg font-semibold">{card.title}</DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              {card.company || "Company not set"} · added {formatRelative(card.created_at)}
            </DialogDescription>
          </div>

          <div role="radiogroup" aria-label="Status" className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {STATUSES.map((status) => {
              const selected = status.id === card.status;
              return (
                <button
                  key={status.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => !selected && onMove(card.id, status.id, 0)}
                  className={cn(
                    "flex items-center justify-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium transition-colors hover:border-primary/40",
                    selected && "border-primary bg-accent text-accent-foreground ring-1 ring-primary",
                  )}
                >
                  <span className={cn("size-2 rounded-full", status.dot)} aria-hidden />
                  {status.label}
                </button>
              );
            })}
          </div>

          {(card.job_id !== null || card.link) && (
            <div className="flex flex-wrap gap-2">
              {card.job_id !== null && (
                <>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/analyze?job=${card.job_id}`}>
                      <Gauge aria-hidden />
                      Match & documents
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/interview-prep?job=${card.job_id}`}>
                      <MessagesSquare aria-hidden />
                      Interview prep
                    </Link>
                  </Button>
                </>
              )}
              {card.link && (
                <Button variant="outline" size="sm" asChild>
                  <a href={card.link} target="_blank" rel="noopener noreferrer">
                    <ExternalLink aria-hidden />
                    Job posting
                  </a>
                </Button>
              )}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Role">{(id) => <Input id={id} value={draft.title} onChange={(e) => set("title", e.target.value)} maxLength={300} />}</Field>
            <Field label="Company">
              {(id) => <Input id={id} value={draft.company} onChange={(e) => set("company", e.target.value)} maxLength={300} />}
            </Field>
            <Field label="Link to the posting" hint={linkInvalid ? "Links must start with http:// or https://" : undefined}>
              {(id) => (
                <Input
                  id={id}
                  type="url"
                  inputMode="url"
                  placeholder="https://…"
                  value={draft.link}
                  onChange={(e) => set("link", e.target.value)}
                  aria-invalid={linkInvalid}
                />
              )}
            </Field>
            <Field label="Deadline" hint={deadline && card.deadline === draft.deadline ? deadline.text : undefined}>
              {(id) => (
                <div className="flex gap-2">
                  <Input id={id} type="date" value={draft.deadline ?? ""} onChange={(e) => set("deadline", e.target.value || null)} />
                  {draft.deadline && (
                    <Button variant="ghost" size="icon" onClick={() => set("deadline", null)} aria-label="Clear deadline">
                      <X aria-hidden />
                    </Button>
                  )}
                </div>
              )}
            </Field>
            <Field label="Notes" hint="Recruiter names, referral, what you sent, follow-up dates…" className="sm:col-span-2">
              {(id) => <Textarea id={id} rows={5} value={draft.notes} onChange={(e) => set("notes", e.target.value)} maxLength={5000} />}
            </Field>
          </div>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void remove()}
              className={cn("text-destructive hover:text-destructive", confirmDelete && "bg-destructive/10")}
            >
              <Trash2 aria-hidden />
              {confirmDelete ? "Click again to remove" : "Remove from board"}
            </Button>
            <Button onClick={() => void save()} disabled={!dirty || saving || linkInvalid}>
              <Save aria-hidden />
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>

          <section aria-labelledby="timeline-heading" className="border-t border-border pt-5">
            <h3 id="timeline-heading" className="mb-3 inline-flex items-center gap-2 text-sm font-semibold">
              <History className="size-4 text-muted-foreground" aria-hidden />
              Timeline
            </h3>
            <ol className="flex flex-col gap-3 border-l border-border pl-4">
              {[...card.events].reverse().map((event) => (
                <li key={event.id} className="relative text-sm">
                  <span
                    className={cn(
                      "absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-popover",
                      event.kind === "status" ? "bg-primary" : event.kind === "deadline" ? "bg-warning" : "bg-muted-foreground",
                    )}
                    aria-hidden
                  />
                  <span className="font-medium">{event.message}</span>
                  <span className="block text-xs text-muted-foreground">{formatRelative(event.created_at)}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
