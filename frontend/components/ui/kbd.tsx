import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** Keyboard shortcut hint, e.g. <Kbd>Ctrl K</Kbd>. */
export function Kbd({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <kbd
      className={cn(
        "inline-flex h-6 items-center rounded-md border border-border bg-muted px-1.5 font-sans text-[11px] font-medium text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
