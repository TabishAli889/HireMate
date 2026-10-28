"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { BackendStatus } from "@/components/layout/backend-status";
import { Logo } from "@/components/layout/logo";
import { useShell } from "@/components/layout/shell-provider";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Kbd } from "@/components/ui/kbd";

/** Sticky header: mobile logo, command-palette trigger, API status, theme toggle. */
export function Topbar() {
  const { setPaletteOpen } = useShell();
  const [shortcut, setShortcut] = useState("Ctrl K");

  useEffect(() => {
    if (/mac|iphone|ipad/i.test(navigator.userAgent)) setShortcut("⌘K");
  }, []);

  return (
    <header className="sticky top-0 z-30 flex h-topbar items-center gap-3 border-b border-border/70 bg-background/70 px-4 backdrop-blur-xl md:px-8">
      <Logo showWordmark className="md:hidden" />

      <button
        type="button"
        onClick={() => setPaletteOpen(true)}
        aria-label="Search pages and actions"
        aria-keyshortcuts="Control+K Meta+K"
        className="ml-auto flex size-10 items-center justify-center gap-2 rounded-xl border border-border bg-card/60 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground sm:ml-0 sm:h-10 sm:w-full sm:max-w-sm sm:justify-start sm:px-3"
      >
        <Search className="size-4 shrink-0" aria-hidden />
        <span className="hidden sm:inline">Search or jump to…</span>
        <Kbd className="ml-auto hidden sm:inline-flex">{shortcut}</Kbd>
      </button>

      <div className="flex items-center gap-2 sm:ml-auto">
        <BackendStatus />
        <ThemeToggle />
      </div>
    </header>
  );
}
