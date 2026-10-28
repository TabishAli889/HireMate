import type { Seniority } from "@/types/job";

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

/** Parse a backend timestamp. The API stores UTC; values without a zone suffix are treated as UTC. */
export function parseUtc(iso: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`);
}

/** "3 hours ago", "yesterday", "just now". */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const seconds = (parseUtc(iso).getTime() - now.getTime()) / 1000;
  if (Number.isNaN(seconds)) return "";
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export const SENIORITY_LABEL: Record<Seniority, string> = {
  internship: "Internship",
  entry: "Entry level",
  mid: "Mid level",
  senior: "Senior",
  unknown: "Level not stated",
};

export type ScoreBand = { label: string; tone: "success" | "primary" | "warning" };

/** Plain-language label and colour for a 0-100 match score. */
export function scoreBand(score: number): ScoreBand {
  if (score >= 75) return { label: "Strong match", tone: "success" };
  if (score >= 50) return { label: "Good match", tone: "primary" };
  if (score >= 30) return { label: "Stretch role", tone: "warning" };
  return { label: "Big stretch", tone: "warning" };
}
