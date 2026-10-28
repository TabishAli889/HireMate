"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, apiFetch } from "@/lib/api";
import { STATUSES } from "@/lib/applications";
import type { Application, ApplicationCreateBody, ApplicationStatus } from "@/types/application";
import type { JobSummary } from "@/types/job";

const SELECT_CLASS =
  "flex h-10 w-full rounded-xl border border-input bg-card/60 px-3 text-sm focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30";

interface NewApplicationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (card: Application) => void;
}

/** Add a card: pick an analyzed job (details filled in for you) or type any role by hand. */
export function NewApplicationDialog({ open, onOpenChange, onCreated }: NewApplicationDialogProps) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [jobId, setJobId] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [link, setLink] = useState("");
  const [status, setStatus] = useState<ApplicationStatus>("saved");
  const [deadline, setDeadline] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setJobId("");
    setTitle("");
    setCompany("");
    setLink("");
    setStatus("saved");
    setDeadline("");
    apiFetch<JobSummary[]>("/jobs?limit=100")
      .then((all) => setJobs(all.filter((job) => job.application_status === null)))
      .catch(() => setJobs([]));
  }, [open]);

  const fromJob = jobId !== "";
  const linkInvalid = link.trim() !== "" && !/^https?:\/\//i.test(link.trim());
  const canSubmit = !busy && !linkInvalid && (fromJob || title.trim().length > 0);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    const body: ApplicationCreateBody = fromJob
      ? { job_id: Number(jobId), status, deadline: deadline || null }
      : { title: title.trim(), company: company.trim(), link: link.trim(), status, deadline: deadline || null };
    setBusy(true);
    try {
      onCreated(await apiFetch<Application>("/applications", { method: "POST", body: JSON.stringify(body) }));
      onOpenChange(false);
      toast.success("Added to your board");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't add it.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[8%] max-h-[88vh] overflow-y-auto p-5 sm:p-6">
        <DialogTitle className="text-lg font-semibold">Add an application</DialogTitle>
        <DialogDescription className="mt-1 text-sm text-muted-foreground">
          Pick a job you analyzed, or add any other role by hand.
        </DialogDescription>

        <form onSubmit={(e) => void submit(e)} className="mt-5 flex flex-col gap-4">
          {jobs.length > 0 && (
            <Field label="Analyzed job" hint={fromJob ? "Title, company and link come from the analysis." : undefined}>
              {(id) => (
                <select id={id} value={jobId} onChange={(e) => setJobId(e.target.value)} className={SELECT_CLASS}>
                  <option value="">— Add a role by hand —</option>
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.title || "Untitled role"}
                      {job.company ? ` · ${job.company}` : ""}
                      {job.match_score !== null ? ` (${job.match_score}%)` : ""}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          )}

          {!fromJob && (
            <>
              <Field label="Role">
                {(id) => <Input id={id} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. AI Engineering Intern" required maxLength={300} />}
              </Field>
              <Field label="Company">
                {(id) => <Input id={id} value={company} onChange={(e) => setCompany(e.target.value)} maxLength={300} />}
              </Field>
              <Field label="Link to the posting" hint={linkInvalid ? "Links must start with http:// or https://" : undefined}>
                {(id) => (
                  <Input id={id} type="url" inputMode="url" placeholder="https://…" value={link} onChange={(e) => setLink(e.target.value)} aria-invalid={linkInvalid} />
                )}
              </Field>
            </>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Column">
              {(id) => (
                <select id={id} value={status} onChange={(e) => setStatus(e.target.value as ApplicationStatus)} className={SELECT_CLASS}>
                  {STATUSES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <Field label="Deadline (optional)">
              {(id) => <Input id={id} type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />}
            </Field>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              <Plus aria-hidden />
              {busy ? "Adding…" : "Add to board"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
