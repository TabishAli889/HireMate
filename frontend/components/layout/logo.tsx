import Link from "next/link";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogoProps {
  showWordmark?: boolean;
  className?: string;
}

/** HireMate mark: gradient tile + wordmark, links home. */
export function Logo({ showWordmark = true, className }: LogoProps) {
  return (
    <Link
      href="/"
      aria-label="HireMate home"
      className={cn("flex items-center gap-2.5 rounded-xl focus-visible:outline-offset-4", className)}
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand text-[hsl(var(--gradient-foreground))] shadow-glow">
        <Sparkles className="size-[18px]" aria-hidden />
      </span>
      {showWordmark && <span className="font-heading text-lg font-bold tracking-tight">HireMate</span>}
    </Link>
  );
}
