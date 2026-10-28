"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface FieldProps {
  label: string;
  hint?: string;
  className?: string;
  /** Receives the generated id to put on the input. */
  children: (id: string) => ReactNode;
}

/** Label + control + optional hint, wired together with a generated id. */
export function Field({ label, hint, className, children }: FieldProps) {
  const id = useId();
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children(id)}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
