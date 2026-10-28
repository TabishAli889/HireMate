"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Logo } from "@/components/layout/logo";
import { useShell } from "@/components/layout/shell-provider";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { NAV_ITEMS, isActivePath, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

function SidebarLink({ item, active, collapsed }: { item: NavItem; active: boolean; collapsed: boolean }) {
  const Icon = item.icon;
  const link = (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      aria-label={collapsed ? item.label : undefined}
      className={cn(
        "relative flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
        active && "text-accent-foreground hover:bg-transparent hover:text-accent-foreground",
      )}
    >
      {active && (
        <motion.span
          layoutId="sidebar-active-pill"
          className="absolute inset-0 rounded-xl bg-accent"
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        />
      )}
      <Icon className={cn("relative size-5 shrink-0", active && "text-primary")} aria-hidden />
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -4 }}
            transition={{ duration: 0.15 }}
            className="relative truncate"
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>
    </Link>
  );

  if (!collapsed) return link;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{item.label}</TooltipContent>
    </Tooltip>
  );
}

/** Collapsible desktop navigation. Hidden below the `md` breakpoint (mobile uses the tab bar). */
export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed: collapsed, toggleSidebar } = useShell();
  const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <aside
      style={{ width: collapsed ? "var(--sidebar-width-collapsed)" : "var(--sidebar-width)" }}
      className="sticky top-0 z-40 hidden h-dvh shrink-0 flex-col border-r border-border/70 bg-card/50 backdrop-blur-xl transition-[width] duration-300 ease-out md:flex"
    >
      <div className={cn("flex h-topbar items-center px-4", collapsed && "justify-center px-0")}>
        <Logo showWordmark={!collapsed} />
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        <ul className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <li key={item.href}>
              <SidebarLink item={item} active={isActivePath(pathname, item.href)} collapsed={collapsed} />
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-border/70 p-3">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          className={cn(
            "flex h-10 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
            collapsed && "justify-center px-0",
          )}
        >
          <ToggleIcon className="size-5 shrink-0" aria-hidden />
          {!collapsed && <span className="truncate">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
