"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner } from "sonner";

/** App-wide toast host, themed to match light/dark mode. */
export function Toaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Sonner
      theme={resolvedTheme === "dark" ? "dark" : "light"}
      position="bottom-right"
      offset={88}
      richColors
      closeButton
      toastOptions={{ className: "!rounded-2xl !font-sans" }}
    />
  );
}
