"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EntryCardProps {
  title: string;
  onRemove: () => void;
  children: ReactNode;
}

/** One editable entry (a job, a degree, a project) inside a section. */
export function EntryCard({ title, onRemove, children }: EntryCardProps) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden rounded-xl border border-border bg-background/40"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
        <h3 className="truncate text-sm font-semibold">{title}</h3>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRemove}
          aria-label={`Remove ${title}`}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 aria-hidden />
          <span className="hidden sm:inline">Remove</span>
        </Button>
      </div>
      <div className="flex flex-col gap-4 p-4">{children}</div>
    </motion.li>
  );
}
