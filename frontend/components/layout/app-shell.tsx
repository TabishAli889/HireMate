import type { ReactNode } from "react";
import { CommandPalette } from "@/components/layout/command-palette";
import { MobileTabBar } from "@/components/layout/mobile-tab-bar";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

/** Page frame: sidebar (desktop) + top bar + content + tab bar (mobile). */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-card focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-soft"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main
          id="main"
          tabIndex={-1}
          className="flex-1 px-4 pb-[calc(var(--tabbar-height)+2rem)] pt-6 focus:outline-none md:px-8 md:pb-12 md:pt-8"
        >
          <div className="mx-auto w-full max-w-content">{children}</div>
        </main>
      </div>
      <MobileTabBar />
      <CommandPalette />
    </div>
  );
}
