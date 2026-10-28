import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** Shimmer placeholder shown while content loads — never a blank screen. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden className={cn("animate-pulse rounded-xl bg-muted", className)} {...props} />;
}
