"use client";

import { useMemo, useState } from "react";
import { Check, Pencil, TriangleAlert, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { diffWords, type DiffPart } from "@/lib/diff";
import { cn } from "@/lib/utils";
import type { BulletStatus, BulletSuggestion } from "@/types/job";

const PLACEHOLDER = "[add real number]";

/** Marks the tokens that make up "[add real number]" so they can be highlighted. */
function withPlaceholder(parts: DiffPart[]): (DiffPart & { placeholder: boolean })[] {
  let inside = false;
  return parts.map((part) => {
    if (part.text.includes("[add")) inside = true;
    const flagged = inside;
    if (part.text.includes("]")) inside = false;
    return { ...part, placeholder: flagged };
  });
}

interface BulletReviewProps {
  bullet: BulletSuggestion;
  onDecide: (status: BulletStatus) => void;
  onSaveEdit: (text: string) => void;
  disabled: boolean;
}

/** One rewritten bullet: before/after with word-level highlights, accept / reject / edit. */
export function BulletReview({ bullet, onDecide, onSaveEdit, disabled }: BulletReviewProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(bullet.tailored);
  const diff = useMemo(() => diffWords(bullet.original, bullet.tailored), [bullet.original, bullet.tailored]);
  const after = useMemo(() => withPlaceholder(diff.after), [diff.after]);
  const hasPlaceholder = bullet.tailored.includes(PLACEHOLDER);

  return (
    <li
      className={cn(
        "rounded-xl border bg-background/40 p-4 transition-colors",
        bullet.status === "accepted" && "border-success/50",
        bullet.status === "rejected" && "border-border opacity-75",
        bullet.status === "pending" && "border-primary/30",
      )}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Before</p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {diff.before.map((part, i) =>
              part.type === "removed" ? (
                <del key={i} className="rounded bg-destructive/10 px-0.5 text-destructive decoration-destructive/50">
                  {part.text}
                </del>
              ) : (
                <span key={i}>{part.text}</span>
              ),
            )}
          </p>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">After</p>
          {editing ? (
            <Textarea
              rows={3}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label={`Edit tailored bullet for ${bullet.context}`}
              autoFocus
            />
          ) : (
            <p className="text-sm leading-relaxed">
              {after.map((part, i) =>
                part.placeholder ? (
                  <mark key={i} className="rounded bg-warning-soft px-0.5 font-medium text-warning">
                    {part.text}
                  </mark>
                ) : part.type === "added" ? (
                  <ins key={i} className="rounded bg-success-soft px-0.5 text-success no-underline">
                    {part.text}
                  </ins>
                ) : (
                  <span key={i}>{part.text}</span>
                ),
              )}
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {bullet.reason && <Badge variant="muted">Highlights: {bullet.reason}</Badge>}
          {hasPlaceholder && !editing && (
            <span className="inline-flex items-center gap-1 text-xs text-warning">
              <TriangleAlert className="size-3.5" aria-hidden />
              Replace {PLACEHOLDER} with a real figure (Edit), or reject.
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {editing ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => { setDraft(bullet.tailored); setEditing(false); }}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={disabled || draft.trim().length < 3}
                onClick={() => {
                  onSaveEdit(draft.trim());
                  setEditing(false);
                }}
              >
                <Check aria-hidden />
                Save & accept
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => setEditing(true)} disabled={disabled}>
                <Pencil aria-hidden />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                aria-pressed={bullet.status === "rejected"}
                onClick={() => onDecide(bullet.status === "rejected" ? "pending" : "rejected")}
                disabled={disabled}
                className={cn(bullet.status === "rejected" && "border-destructive/50 text-destructive")}
              >
                <X aria-hidden />
                {bullet.status === "rejected" ? "Rejected" : "Reject"}
              </Button>
              <Button
                variant={bullet.status === "accepted" ? "default" : "outline"}
                size="sm"
                aria-pressed={bullet.status === "accepted"}
                onClick={() => onDecide(bullet.status === "accepted" ? "pending" : "accepted")}
                disabled={disabled}
              >
                <Check aria-hidden />
                {bullet.status === "accepted" ? "Accepted" : "Accept"}
              </Button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}
