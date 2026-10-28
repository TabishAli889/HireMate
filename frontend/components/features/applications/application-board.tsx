"use client";

import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { ApplicationCard } from "@/components/features/applications/application-card";
import { STATUSES, groupByStatus } from "@/lib/applications";
import { cn } from "@/lib/utils";
import type { Application, ApplicationStatus } from "@/types/application";

interface DropTarget {
  status: ApplicationStatus;
  index: number;
}

interface ApplicationBoardProps {
  cards: Application[];
  onMove: (id: number, status: ApplicationStatus, position: number) => void;
  onOpen: (card: Application) => void;
}

/**
 * Five columns. Cards move by drag and drop (mouse) or Alt + arrow keys (keyboard):
 * Alt+←/→ changes column, Alt+↑/↓ changes order. On touch screens, open a card and pick a status.
 */
export function ApplicationBoard({ cards, onMove, onOpen }: ApplicationBoardProps) {
  const instructionsId = useId();
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [drop, setDrop] = useState<DropTarget | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const listRefs = useRef<Partial<Record<ApplicationStatus, HTMLOListElement | null>>>({});
  const groups = groupByStatus(cards);

  /** Index the dragged card would land at, from the pointer's height over the column's cards. */
  const indexAt = (status: ApplicationStatus, clientY: number): number => {
    const list = listRefs.current[status];
    if (!list) return 0;
    let index = 0;
    for (const item of Array.from(list.querySelectorAll<HTMLElement>("[data-card-id]"))) {
      if (Number(item.dataset.cardId) === draggingId) continue;
      const box = item.getBoundingClientRect();
      if (clientY > box.top + box.height / 2) index += 1;
    }
    return index;
  };

  const onDragOver = (status: ApplicationStatus) => (event: DragEvent<HTMLElement>) => {
    if (draggingId === null) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    const index = indexAt(status, event.clientY);
    if (drop?.status !== status || drop.index !== index) setDrop({ status, index });
  };

  const onDrop = (status: ApplicationStatus) => (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    const id = draggingId ?? Number(event.dataTransfer.getData("text/plain"));
    const index = drop?.status === status ? drop.index : indexAt(status, event.clientY);
    setDraggingId(null);
    setDrop(null);
    if (!id) return;
    const card = cards.find((c) => c.id === id);
    const from = card ? groups[card.status].findIndex((c) => c.id === id) : -1;
    if (card && card.status === status && from === index) return; // dropped where it was
    onMove(id, status, index);
  };

  const onKeyMove = (card: Application) => (event: KeyboardEvent<HTMLElement>) => {
    if (!event.altKey) return;
    const column = STATUSES.findIndex((s) => s.id === card.status);
    const list = groups[card.status];
    const index = list.findIndex((c) => c.id === card.id);
    let target: DropTarget | null = null;
    if (event.key === "ArrowLeft" && column > 0) target = { status: STATUSES[column - 1]!.id, index: 0 };
    if (event.key === "ArrowRight" && column < STATUSES.length - 1) target = { status: STATUSES[column + 1]!.id, index: 0 };
    if (event.key === "ArrowUp" && index > 0) target = { status: card.status, index: index - 1 };
    if (event.key === "ArrowDown" && index < list.length - 1) target = { status: card.status, index: index + 1 };
    if (!target) return;
    const { status, index: position } = target;
    event.preventDefault();
    onMove(card.id, status, position);
    const label = STATUSES.find((s) => s.id === status)?.label;
    setAnnouncement(`${card.title} moved to ${label}, position ${position + 1}.`);
    // Keep focus on the moved card once it re-renders in its new place.
    requestAnimationFrame(() =>
      document.querySelector<HTMLElement>(`[data-card-id="${card.id}"] [role="button"]`)?.focus(),
    );
  };

  return (
    <>
      <p id={instructionsId} className="sr-only">
        Press Enter to open. Press Alt with the left or right arrow to move between columns, Alt with up or down to reorder.
      </p>
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      <div className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-4 sm:mx-0 sm:px-0 xl:grid xl:grid-cols-5 xl:overflow-visible">
        {STATUSES.map((status) => {
          const list = groups[status.id];
          const dropIndex = drop && drop.status === status.id ? drop.index : null;
          const isTarget = dropIndex !== null;
          return (
            <section
              key={status.id}
              aria-labelledby={`${instructionsId}-${status.id}`}
              onDragOver={onDragOver(status.id)}
              onDrop={onDrop(status.id)}
              onDragLeave={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDrop(null);
              }}
              className={cn(
                "flex w-72 shrink-0 snap-start flex-col rounded-2xl border border-transparent bg-muted/50 p-2 transition-colors xl:w-auto",
                isTarget && "border-primary/40 bg-accent/40",
              )}
            >
              <header className="flex items-center gap-2 px-2 pb-2 pt-1">
                <span className={cn("size-2 rounded-full", status.dot)} aria-hidden />
                <h2 id={`${instructionsId}-${status.id}`} className="text-sm font-semibold">
                  {status.label}
                </h2>
                <span className="ml-auto rounded-md bg-card px-1.5 text-xs font-medium tabular-nums text-muted-foreground">
                  {list.length}
                </span>
              </header>
              <ol
                ref={(el) => {
                  listRefs.current[status.id] = el;
                }}
                className="flex min-h-24 flex-1 flex-col gap-2"
              >
                {list.map((card, index) => (
                  <li key={card.id} className="flex flex-col gap-2">
                    {card.id !== draggingId &&
                      dropIndex === list.slice(0, index).filter((c) => c.id !== draggingId).length && <DropLine />}
                    <ApplicationCard
                      card={card}
                      dragging={draggingId === card.id}
                      instructionsId={instructionsId}
                      onOpen={() => onOpen(card)}
                      onKeyMove={onKeyMove(card)}
                      onDragStart={(event) => {
                        event.dataTransfer.effectAllowed = "move";
                        event.dataTransfer.setData("text/plain", String(card.id));
                        setDraggingId(card.id);
                      }}
                      onDragEnd={() => {
                        setDraggingId(null);
                        setDrop(null);
                      }}
                    />
                  </li>
                ))}
                {dropIndex !== null && dropIndex >= list.filter((c) => c.id !== draggingId).length && (
                  <li aria-hidden>
                    <DropLine />
                  </li>
                )}
                {list.length === 0 && !isTarget && (
                  <li className="grid flex-1 place-items-center rounded-xl border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">
                    {status.hint}
                  </li>
                )}
              </ol>
            </section>
          );
        })}
      </div>
    </>
  );
}

function DropLine() {
  return <div aria-hidden className="h-1 rounded-full bg-primary" />;
}
