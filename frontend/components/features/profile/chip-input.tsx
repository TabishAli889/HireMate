"use client";

import { useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChipInputProps {
  values: string[];
  onChange: (values: string[]) => void;
  /** Accessible name, e.g. "Skills". */
  label: string;
  placeholder?: string;
  className?: string;
}

/** Editable tag list: Enter or comma adds, × or Backspace removes, duplicates are ignored. */
export function ChipInput({ values, onChange, label, placeholder = "Type and press Enter", className }: ChipInputProps) {
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const existing = new Set(values.map((v) => v.toLowerCase()));
    const next = [...values];
    for (const part of raw.split(",")) {
      const value = part.trim().replace(/\s+/g, " ");
      if (value && !existing.has(value.toLowerCase())) {
        existing.add(value.toLowerCase());
        next.push(value);
      }
    }
    if (next.length !== values.length) onChange(next);
    setDraft("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      add(draft);
    } else if (event.key === "Backspace" && draft === "" && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  };

  return (
    <div
      className={cn(
        "flex min-h-11 flex-wrap items-center gap-2 rounded-xl border border-input bg-card/60 p-2 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-ring/30",
        className,
      )}
    >
      <ul className="contents" aria-label={label}>
        <AnimatePresence initial={false}>
          {values.map((value) => (
            <motion.li
              key={value}
              layout
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.15 }}
              className="inline-flex max-w-full items-center gap-1 rounded-lg bg-accent py-1 pl-2.5 pr-1 text-xs font-medium text-accent-foreground"
            >
              <span className="truncate">{value}</span>
              <button
                type="button"
                onClick={() => onChange(values.filter((v) => v !== value))}
                aria-label={`Remove ${value}`}
                className="grid size-5 place-items-center rounded-md transition-colors hover:bg-primary/15"
              >
                <X className="size-3" aria-hidden />
              </button>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      <div className="flex min-w-[10rem] flex-1 items-center gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => draft.trim() && add(draft)}
          placeholder={placeholder}
          aria-label={`Add to ${label}`}
          className="h-7 w-full bg-transparent px-1 text-sm outline-none placeholder:text-muted-foreground"
        />
        {draft.trim() && (
          <button
            type="button"
            onClick={() => add(draft)}
            aria-label={`Add “${draft.trim()}”`}
            className="grid size-7 shrink-0 place-items-center rounded-lg text-primary hover:bg-accent"
          >
            <Plus className="size-4" aria-hidden />
          </button>
        )}
      </div>
    </div>
  );
}
