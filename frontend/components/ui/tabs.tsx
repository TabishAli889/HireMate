"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  /** Small trailing element, e.g. a count. */
  badge?: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  value: string;
  onValueChange: (id: string) => void;
  /** Accessible name for the tab list. */
  label: string;
  className?: string;
  children: ReactNode;
}

/** Accessible tabs (arrow keys, Home/End) with an animated active pill. Renders the active panel's children. */
export function Tabs({ items, value, onValueChange, label, className, children }: TabsProps) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const current = items.findIndex((item) => item.id === value);
    const last = items.length - 1;
    const next =
      event.key === "ArrowRight" ? (current + 1) % items.length
      : event.key === "ArrowLeft" ? (current - 1 + items.length) % items.length
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : -1;
    const target = items[next];
    if (next < 0 || !target) return;
    event.preventDefault();
    onValueChange(target.id);
    refs.current[next]?.focus();
  };

  return (
    <div className={className}>
      <div
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
        className="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl bg-muted p-1"
      >
        {items.map((item, index) => {
          const selected = item.id === value;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[index] = el;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${item.id}`}
              aria-selected={selected}
              aria-controls={`${base}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onValueChange(item.id)}
              className={cn(
                "relative flex h-9 shrink-0 items-center rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground",
                selected && "text-foreground",
              )}
            >
              {selected && (
                <motion.span
                  layoutId={`${base}-pill`}
                  className="absolute inset-0 rounded-lg bg-card shadow-soft"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              <span className="relative inline-flex items-center gap-2">
                {Icon && <Icon className="size-4" aria-hidden />}
                {item.label}
                {item.badge}
              </span>
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${base}-panel`}
        aria-labelledby={`${base}-tab-${value}`}
        tabIndex={0}
        className="mt-6 rounded-2xl focus-visible:outline-offset-4"
      >
        {children}
      </div>
    </div>
  );
}
