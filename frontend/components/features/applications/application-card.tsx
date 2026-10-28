"use client";

import type { DragEvent, KeyboardEvent } from "react";
import { CalendarClock, FilePen, Mail, MessagesSquare, StickyNote } from "lucide-react";
import { DEADLINE_CLASS, deadlineInfo } from "@/lib/applications";
import { scoreBand } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Application } from "@/types/application";

const SCORE_CLASS = {
  success: "bg-success-soft text-success",
  primary: "bg-accent text-accent-foreground",
  warning: "bg-warning-soft text-warning",
} as const;

interface ApplicationCardProps {
  card: Application;
  dragging: boolean;
  onOpen: () => void;
  onDragStart: (event: DragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  onKeyMove: (event: KeyboardEvent<HTMLElement>) => void;
  instructionsId: string;
}

/** One application on the board. Drag it, click it, or use Alt + arrow keys to move it. */
export function ApplicationCard({ card, dragging, onOpen, onDragStart, onDragEnd, onKeyMove, instructionsId }: ApplicationCardProps) {
  const closed = card.status === "offer" || card.status === "rejected";
  const deadline = card.deadline && !closed ? deadlineInfo(card.deadline) : null;
  const band = card.match_score !== null ? scoreBand(card.match_score) : null;
  const docs = [
    card.has_tailoring && { icon: FilePen, label: "Tailored resume" },
    card.has_cover_letter && { icon: Mail, label: "Cover letter" },
    card.has_interview_prep && { icon: MessagesSquare, label: "Interview prep" },
    card.notes.trim() && { icon: StickyNote, label: "Has notes" },
  ].filter(Boolean) as { icon: typeof Mail; label: string }[];

  return (
    <div
      data-card-id={card.id}
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        "group rounded-xl border border-border bg-card shadow-soft transition-[opacity,transform,border-color] hover:border-primary/40",
        dragging && "rotate-1 opacity-40",
      )}
    >
      {/* A div, not a <button>: Firefox won't start a drag from a button. */}
      <div
        role="button"
        tabIndex={0}
        onClick={onOpen}
        onKeyDown={(event) => {
          if ((event.key === "Enter" || event.key === " ") && !event.altKey) {
            event.preventDefault();
            onOpen();
            return;
          }
          onKeyMove(event);
        }}
        aria-describedby={instructionsId}
        className="flex w-full cursor-grab flex-col gap-2 rounded-xl p-3.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing"
      >
        <span className="flex items-start justify-between gap-2">
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{card.title}</span>
            {card.company && <span className="block truncate text-xs text-muted-foreground">{card.company}</span>}
          </span>
          {band && card.match_score !== null && (
            <span
              className={cn("shrink-0 rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums", SCORE_CLASS[band.tone])}
              title={`${band.label}: ${card.match_score}/100`}
            >
              {card.match_score}%
            </span>
          )}
        </span>

        {(deadline || docs.length > 0) && (
          <span className="flex flex-wrap items-center gap-1.5">
            {deadline && (
              <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium", DEADLINE_CLASS[deadline.tone])}>
                <CalendarClock className="size-3" aria-hidden />
                {deadline.text}
              </span>
            )}
            {docs.length > 0 && (
              <span className="ml-auto flex items-center gap-1 text-muted-foreground">
                {docs.map(({ icon: Icon, label }) => (
                  <Icon key={label} className="size-3.5" role="img" aria-label={label} />
                ))}
              </span>
            )}
          </span>
        )}
      </div>
    </div>
  );
}
