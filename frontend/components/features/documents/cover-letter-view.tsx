"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Download, Mail, RefreshCw, Save, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { GenerateCard, StaleNote, isStale, type DocumentViewProps } from "@/components/features/documents/shared";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiFetch } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CoverLetter, Job, Tone } from "@/types/job";

const TONES: { id: Tone; label: string; hint: string }[] = [
  { id: "professional", label: "Professional", hint: "Formal and concise" },
  { id: "friendly", label: "Friendly", hint: "Warm and conversational" },
  { id: "confident", label: "Confident", hint: "Direct and assertive" },
];

/** Cover letter tab: three tones, editable text, honesty warnings, copy and PDF export. */
export function CoverLetterView({ job, onJobChange, agentBusy }: DocumentViewProps) {
  const firstExisting = TONES.find((t) => job.cover_letters[t.id])?.id ?? "professional";
  const [tone, setTone] = useState<Tone>(firstExisting);
  const letter = job.cover_letters[tone];
  const [draft, setDraft] = useState(letter?.body ?? "");
  const [busy, setBusy] = useState<"generate" | "save" | null>(null);
  const [confirmRegenerate, setConfirmRegenerate] = useState(false);

  useEffect(() => {
    setDraft(letter?.body ?? "");
    setConfirmRegenerate(false);
  }, [letter?.body, tone]);

  useEffect(() => {
    if (!confirmRegenerate) return;
    const id = window.setTimeout(() => setConfirmRegenerate(false), 4000);
    return () => window.clearTimeout(id);
  }, [confirmRegenerate]);

  const dirty = letter !== undefined && draft !== letter.body;
  const words = draft.trim() ? draft.trim().split(/\s+/).length : 0;

  const store = (saved: CoverLetter) =>
    onJobChange((j: Job) => ({ ...j, cover_letters: { ...j.cover_letters, [saved.tone]: saved } }));

  const generate = async (regenerate: boolean) => {
    setBusy("generate");
    try {
      store(await apiFetch<CoverLetter>(`/jobs/${job.id}/cover-letter`, { method: "POST", body: JSON.stringify({ tone, regenerate }) }));
      toast.success(`${TONES.find((t) => t.id === tone)?.label} cover letter ready`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't write the cover letter.");
    } finally {
      setBusy(null);
      setConfirmRegenerate(false);
    }
  };

  const save = async () => {
    setBusy("save");
    try {
      store(await apiFetch<CoverLetter>(`/jobs/${job.id}/cover-letter/${tone}`, { method: "PUT", body: JSON.stringify({ body: draft }) }));
      toast.success("Cover letter saved");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't save your edits.");
    } finally {
      setBusy(null);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(draft);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Couldn't access the clipboard. Select the text and copy it manually.");
    }
  };

  const onRegenerate = () => {
    if (letter?.edited && !confirmRegenerate) {
      setConfirmRegenerate(true);
      return;
    }
    void generate(true);
  };

  const disabled = agentBusy || busy !== null;

  return (
    <div className="flex flex-col gap-6">
      <div role="radiogroup" aria-label="Cover letter tone" className="grid gap-2 sm:grid-cols-3">
        {TONES.map((option) => {
          const selected = option.id === tone;
          const exists = Boolean(job.cover_letters[option.id]);
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => setTone(option.id)}
              disabled={busy !== null}
              className={cn(
                "flex items-center justify-between gap-3 rounded-xl border border-border bg-card/40 px-4 py-3 text-left transition-colors hover:border-primary/40",
                selected && "border-primary bg-accent ring-1 ring-primary",
              )}
            >
              <span>
                <span className={cn("block text-sm font-medium", selected && "text-accent-foreground")}>{option.label}</span>
                <span className="block text-xs text-muted-foreground">{option.hint}</span>
              </span>
              {exists && <Check className="size-4 shrink-0 text-success" aria-label="Written" />}
            </button>
          );
        })}
      </div>

      {!letter ? (
        <GenerateCard
          icon={Mail}
          title={`Write a ${tone} cover letter`}
          description="Built only from your real projects and experience. Skills you're missing are never claimed, and anything worth double-checking is flagged."
          actionLabel="Write cover letter"
          onAction={() => void generate(false)}
          busy={busy === "generate" || agentBusy}
          busyLabel="Writing your letter…"
        />
      ) : (
        <>
          {!letter.edited && isStale(job, letter.profile_fingerprint) && (
            <StaleNote what="this letter" onRegenerate={() => void generate(true)} busy={disabled} />
          )}

          {letter.warnings.length > 0 && (
            <Card role="note" className="border-warning/40 p-4">
              <h3 className="inline-flex items-center gap-2 text-sm font-semibold text-warning">
                <TriangleAlert className="size-4" aria-hidden />
                Double-check before sending
              </h3>
              <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-sm">
                {letter.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="flex flex-col gap-4 p-5 sm:p-6">
            {busy === "generate" && <Progress value={null} label="Rewriting your letter" />}
            <label htmlFor="cover-letter-body" className="sr-only">
              Cover letter text
            </label>
            <Textarea
              id="cover-letter-body"
              rows={18}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={busy === "generate"}
              className="font-[inherit] text-[15px] leading-7"
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted-foreground">
                {words} words · {letter.edited ? "edited" : "generated"} {formatRelative(letter.edited ? letter.updated_at : letter.generated_at)}
                {dirty && " · unsaved changes"}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="ghost" size="sm" onClick={onRegenerate} disabled={disabled}>
                  <RefreshCw className={cn(busy === "generate" && "animate-spin")} aria-hidden />
                  {confirmRegenerate ? "Replace my edits?" : "Regenerate"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => void copy()} disabled={!draft.trim()}>
                  <Copy aria-hidden />
                  Copy
                </Button>
                {dirty ? (
                  <Button size="sm" onClick={() => void save()} disabled={disabled || draft.trim().length < 20}>
                    <Save aria-hidden />
                    {busy === "save" ? "Saving…" : "Save edits"}
                  </Button>
                ) : (
                  <Button size="sm" asChild>
                    <a href={`/api/backend/jobs/${job.id}/cover-letter/${tone}/pdf`} download>
                      <Download aria-hidden />
                      Export PDF
                    </a>
                  </Button>
                )}
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
