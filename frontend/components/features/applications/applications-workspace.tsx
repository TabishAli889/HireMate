"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CalendarClock, Plus, SquareKanban } from "lucide-react";
import { toast } from "sonner";
import { ApplicationBoard } from "@/components/features/applications/application-board";
import { ApplicationDialog } from "@/components/features/applications/application-dialog";
import { NewApplicationDialog } from "@/components/features/applications/new-application-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch } from "@/lib/api";
import { STATUSES, deadlineInfo, moveLocally } from "@/lib/applications";
import type { Application, ApplicationStatus } from "@/types/application";

export function BoardSkeleton() {
  return (
    <div role="status" aria-label="Loading your board" className="flex gap-4 overflow-hidden xl:grid xl:grid-cols-5">
      {STATUSES.map((s) => (
        <Skeleton key={s.id} className="h-80 w-72 shrink-0 rounded-2xl xl:w-auto" />
      ))}
    </div>
  );
}

/** Applications page: the Kanban board, the add dialog and the details dialog (`?open=<id>`). */
export function ApplicationsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [cards, setCards] = useState<Application[] | null>(null);
  const [adding, setAdding] = useState(false);

  const openParam = Number(searchParams.get("open"));
  const openCard = cards?.find((c) => c.id === openParam) ?? null;

  const load = useCallback(async () => {
    try {
      setCards(await apiFetch<Application[]>("/applications"));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't load your board.");
      setCards((current) => current ?? []);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setOpen = (id: number | null) =>
    router.replace(id === null ? "/applications" : `/applications?open=${id}`, { scroll: false });

  const replace = (updated: Application) => setCards((list) => list?.map((c) => (c.id === updated.id ? updated : c)) ?? list);

  const move = async (id: number, status: ApplicationStatus, position: number) => {
    setCards((list) => (list ? moveLocally(list, id, status, position) : list)); // instant feedback
    try {
      const saved = await apiFetch<Application>(`/applications/${id}/move`, {
        method: "POST",
        body: JSON.stringify({ status, position }),
      });
      replace(saved); // adds the new timeline entry
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't move that card. Reloading your board.");
      void load();
    }
  };

  if (cards === null) return <BoardSkeleton />;

  const upcoming = cards
    .filter((c) => c.deadline && c.status !== "offer" && c.status !== "rejected")
    .map((c) => ({ card: c, info: deadlineInfo(c.deadline!) }))
    .filter(({ info }) => info.tone !== "later");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {cards.length === 0
            ? "Nothing tracked yet."
            : `${cards.length} application${cards.length === 1 ? "" : "s"} · drag cards between columns, or open one to add notes and a deadline.`}
        </p>
        <Button onClick={() => setAdding(true)}>
          <Plus aria-hidden />
          Add application
        </Button>
      </div>

      {upcoming.length > 0 && (
        <Card role="note" className="flex flex-col gap-2 border-warning/40 p-4">
          <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-warning">
            <CalendarClock className="size-4" aria-hidden />
            Deadlines coming up
          </h2>
          <ul className="flex flex-wrap gap-2">
            {upcoming.map(({ card, info }) => (
              <li key={card.id}>
                <button
                  type="button"
                  onClick={() => setOpen(card.id)}
                  className="rounded-lg bg-card px-2.5 py-1 text-xs font-medium shadow-soft hover:text-primary"
                >
                  {card.title}
                  {card.company && <span className="text-muted-foreground"> · {card.company}</span>}
                  <span className={info.tone === "overdue" ? "text-destructive" : "text-warning"}> · {info.text}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {cards.length === 0 && (
        <Card className="flex flex-col items-center gap-3 px-6 py-10 text-center">
          <span className="grid size-12 place-items-center rounded-2xl bg-accent text-accent-foreground">
            <SquareKanban className="size-6" aria-hidden />
          </span>
          <h2 className="text-lg font-semibold">Start your board</h2>
          <p className="max-w-md text-sm text-muted-foreground">
            Analyze a job and click <span className="font-medium text-foreground">Save to tracker</span>, run “Prepare application”
            (it saves the job for you), or add any role by hand.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/analyze">Analyze a job</Link>
            </Button>
            <Button onClick={() => setAdding(true)}>
              <Plus aria-hidden />
              Add by hand
            </Button>
          </div>
        </Card>
      )}

      <ApplicationBoard cards={cards} onMove={(id, status, position) => void move(id, status, position)} onOpen={(card) => setOpen(card.id)} />

      <NewApplicationDialog
        open={adding}
        onOpenChange={setAdding}
        onCreated={(card) => setCards((list) => [...(list ?? []), card])}
      />
      {openCard && (
        <ApplicationDialog
          key={openCard.id}
          card={openCard}
          onClose={() => setOpen(null)}
          onSaved={replace}
          onMove={(id, status, position) => void move(id, status, position)}
          onDeleted={(id) => {
            setOpen(null);
            setCards((list) => list?.filter((c) => c.id !== id) ?? list);
            void load(); // pick up the renumbered positions
          }}
        />
      )}
    </div>
  );
}
