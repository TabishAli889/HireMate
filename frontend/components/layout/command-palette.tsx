"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Command } from "cmdk";
import { Monitor, Moon, PanelLeft, Search, Sun, type LucideIcon } from "lucide-react";
import { useShell } from "@/components/layout/shell-provider";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";
import { NAV_ITEMS } from "@/lib/nav";

const GROUP_CLASS =
  "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-muted-foreground";

function PaletteItem({
  icon: Icon,
  label,
  hint,
  keywords,
  onSelect,
}: {
  icon: LucideIcon;
  label: string;
  hint?: ReactNode;
  keywords?: string[];
  onSelect: () => void;
}) {
  return (
    <Command.Item
      value={label}
      keywords={keywords}
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-foreground data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
    >
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <span className="flex-1 truncate">{label}</span>
      {hint && <span className="hidden text-xs text-muted-foreground sm:inline">{hint}</span>}
    </Command.Item>
  );
}

/** Ctrl/⌘+K palette: jump to any page or run quick actions. */
export function CommandPalette() {
  const router = useRouter();
  const { setTheme } = useTheme();
  const { paletteOpen, setPaletteOpen, toggleSidebar, sidebarCollapsed } = useShell();

  const run = (action: () => void) => {
    setPaletteOpen(false);
    action();
  };

  return (
    <Dialog open={paletteOpen} onOpenChange={setPaletteOpen}>
      <DialogContent hideClose className="overflow-hidden p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">Search for a page or action, then press Enter.</DialogDescription>
        <Command label="Command palette" loop>
          <div className="flex items-center gap-3 border-b border-border px-4">
            <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <Command.Input
              autoFocus
              placeholder="Search pages and actions…"
              className="h-14 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <Kbd>Esc</Kbd>
          </div>
          <Command.List className="max-h-[22rem] overflow-y-auto p-2">
            <Command.Empty className="py-10 text-center text-sm text-muted-foreground">
              No matches. Try “profile” or “dark”.
            </Command.Empty>

            <Command.Group heading="Go to" className={GROUP_CLASS}>
              {NAV_ITEMS.map((item) => (
                <PaletteItem
                  key={item.href}
                  icon={item.icon}
                  label={item.label}
                  hint={item.description}
                  keywords={[item.shortLabel, item.description]}
                  onSelect={() => run(() => router.push(item.href))}
                />
              ))}
            </Command.Group>

            <Command.Group heading="Actions" className={GROUP_CLASS}>
              <PaletteItem icon={Sun} label="Light theme" keywords={["theme", "mode"]} onSelect={() => run(() => setTheme("light"))} />
              <PaletteItem icon={Moon} label="Dark theme" keywords={["theme", "mode"]} onSelect={() => run(() => setTheme("dark"))} />
              <PaletteItem icon={Monitor} label="System theme" keywords={["theme", "auto"]} onSelect={() => run(() => setTheme("system"))} />
              <PaletteItem
                icon={PanelLeft}
                label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                keywords={["sidebar", "menu"]}
                hint={<Kbd>Ctrl B</Kbd>}
                onSelect={() => run(toggleSidebar)}
              />
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
