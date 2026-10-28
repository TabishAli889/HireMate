"use client";

import { useState } from "react";
import Link from "next/link";
import { BookmarkPlus, SquareKanban } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api";
import { STATUS_META } from "@/lib/applications";
import { cn } from "@/lib/utils";
import type { Application } from "@/types/application";
import type { Job } from "@/types/job";

interface TrackerButtonProps {
  job: Job;
  onJobChange: (update: (job: Job) => Job) => void;
  disabled?: boolean;
}

/** "Save to tracker" for an analyzed job, or a link to its card once it's on the board. */
export function TrackerButton({ job, onJobChange, disabled = false }: TrackerButtonProps) {
  const [busy, setBusy] = useState(false);

  if (job.application) {
    const meta = STATUS_META[job.application.status];
    return (
      <Button variant="outline" asChild>
        <Link href={`/applications?open=${job.application.id}`}>
          <span className={cn("size-2 rounded-full", meta.dot)} aria-hidden />
          On your board · {meta.label}
        </Link>
      </Button>
    );
  }

  const save = async () => {
    setBusy(true);
    try {
      const card = await apiFetch<Application>("/applications", { method: "POST", body: JSON.stringify({ job_id: job.id }) });
      onJobChange((j) => ({ ...j, application: { id: card.id, status: card.status } }));
      toast.success("Saved to your tracker", {
        action: { label: "Open board", onClick: () => window.location.assign(`/applications?open=${card.id}`) },
      });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't save it to your tracker.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button variant="outline" onClick={() => void save()} disabled={busy || disabled}>
      {busy ? <SquareKanban className="animate-pulse" aria-hidden /> : <BookmarkPlus aria-hidden />}
      Save to tracker
    </Button>
  );
}
