import type { Application, ApplicationStatus } from "@/types/application";

export interface StatusMeta {
  id: ApplicationStatus;
  label: string;
  hint: string;
  /** Tailwind classes for the column's dot / chip. */
  dot: string;
  chip: string;
}

export const STATUSES: StatusMeta[] = [
  { id: "saved", label: "Saved", hint: "Jobs you want to apply to", dot: "bg-muted-foreground", chip: "bg-muted text-muted-foreground" },
  { id: "applied", label: "Applied", hint: "Waiting to hear back", dot: "bg-primary", chip: "bg-accent text-accent-foreground" },
  { id: "interview", label: "Interview", hint: "In the interview process", dot: "bg-warning", chip: "bg-warning-soft text-warning" },
  { id: "offer", label: "Offer", hint: "You got an offer", dot: "bg-success", chip: "bg-success-soft text-success" },
  { id: "rejected", label: "Rejected", hint: "Closed. Keep the notes", dot: "bg-destructive", chip: "bg-destructive/10 text-destructive" },
];

export const STATUS_META = Object.fromEntries(STATUSES.map((s) => [s.id, s])) as Record<ApplicationStatus, StatusMeta>;

/** Cards per column, each sorted by position. */
export function groupByStatus(cards: Application[]): Record<ApplicationStatus, Application[]> {
  const groups = Object.fromEntries(STATUSES.map((s) => [s.id, [] as Application[]])) as Record<ApplicationStatus, Application[]>;
  for (const card of cards) groups[card.status]?.push(card);
  for (const list of Object.values(groups)) list.sort((a, b) => a.position - b.position || a.id - b.id);
  return groups;
}

/**
 * Local copy of the backend's move rule: take the card out, insert it at `position` in the target
 * column, renumber both columns. Lets the board update instantly while the request is in flight.
 */
export function moveLocally(cards: Application[], id: number, status: ApplicationStatus, position: number): Application[] {
  const card = cards.find((c) => c.id === id);
  if (!card) return cards;
  const groups = groupByStatus(cards.filter((c) => c.id !== id));
  const target = groups[status];
  target.splice(Math.min(position, target.length), 0, { ...card, status });
  return STATUSES.flatMap((s) => groups[s.id].map((c, index) => ({ ...c, position: index })));
}

/** Parse "YYYY-MM-DD" as a local calendar date (not UTC midnight). */
export function parseDay(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1);
}

export function formatDay(day: string): string {
  return parseDay(day).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export type DeadlineTone = "overdue" | "soon" | "later";

/** "Due today", "Due in 3 days", "2 days overdue", with a colour tone. */
export function deadlineInfo(day: string, now: Date = new Date()): { text: string; tone: DeadlineTone } {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((parseDay(day).getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return { text: `${-days} day${days === -1 ? "" : "s"} overdue`, tone: "overdue" };
  if (days === 0) return { text: "Due today", tone: "soon" };
  if (days === 1) return { text: "Due tomorrow", tone: "soon" };
  if (days <= 7) return { text: `Due in ${days} days`, tone: "soon" };
  return { text: `Due ${formatDay(day)}`, tone: "later" };
}

export const DEADLINE_CLASS: Record<DeadlineTone, string> = {
  overdue: "bg-destructive/10 text-destructive",
  soon: "bg-warning-soft text-warning",
  later: "bg-muted text-muted-foreground",
};
