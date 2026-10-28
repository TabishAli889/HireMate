import {
  LayoutDashboard,
  MessagesSquare,
  ScanSearch,
  Settings,
  SquareKanban,
  UserRound,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  /** Compact label for the mobile tab bar. */
  shortLabel: string;
  description: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    href: "/",
    label: "Dashboard",
    shortLabel: "Home",
    description: "Overview, stats and next steps",
    icon: LayoutDashboard,
  },
  {
    href: "/profile",
    label: "Profile",
    shortLabel: "Profile",
    description: "Your resume vault",
    icon: UserRound,
  },
  {
    href: "/analyze",
    label: "Analyze Job",
    shortLabel: "Analyze",
    description: "Match a job posting to your profile",
    icon: ScanSearch,
  },
  {
    href: "/applications",
    label: "Applications",
    shortLabel: "Apps",
    description: "Track every application on a board",
    icon: SquareKanban,
  },
  {
    href: "/interview-prep",
    label: "Interview Prep",
    shortLabel: "Prep",
    description: "Likely questions with answer hints",
    icon: MessagesSquare,
  },
  {
    href: "/settings",
    label: "Settings",
    shortLabel: "Settings",
    description: "Theme, API status and your data",
    icon: Settings,
  },
];

/** True when `href` is the current page or one of its sub-pages. */
export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
