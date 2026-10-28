"use client";

import { useTheme } from "next-themes";
import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMounted } from "@/hooks/use-mounted";
import { cn } from "@/lib/utils";

const OPTIONS: { value: "light" | "dark" | "system"; label: string; icon: LucideIcon }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

/** Radio-group theme picker (Light / Dark / System). */
export function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Choose how HireMate looks. System follows your OS setting.</CardDescription>
      </CardHeader>
      <CardContent>
        {!mounted ? (
          <div className="grid grid-cols-3 gap-3">
            {OPTIONS.map((o) => (
              <Skeleton key={o.value} className="h-20" />
            ))}
          </div>
        ) : (
          <div role="radiogroup" aria-label="Theme" className="grid grid-cols-3 gap-3">
            {OPTIONS.map(({ value, label, icon: Icon }) => {
              const selected = theme === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => {
                    setTheme(value);
                    toast.success(`Theme set to ${label.toLowerCase()}`);
                  }}
                  className={cn(
                    "flex h-20 flex-col items-center justify-center gap-2 rounded-xl border border-border bg-card/40 text-sm font-medium text-muted-foreground transition-all hover:border-primary/40 hover:text-foreground",
                    selected && "border-primary bg-accent text-accent-foreground ring-1 ring-primary",
                  )}
                >
                  <Icon className="size-5" aria-hidden />
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
