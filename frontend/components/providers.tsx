"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { MotionConfig } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { ShellProvider } from "@/components/layout/shell-provider";

/** All client-side context providers, mounted once in the root layout. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <MotionConfig reducedMotion="user">
        <TooltipProvider delayDuration={200}>
          <ShellProvider>
            {children}
            <Toaster />
          </ShellProvider>
        </TooltipProvider>
      </MotionConfig>
    </ThemeProvider>
  );
}
