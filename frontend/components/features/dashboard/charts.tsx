"use client";

import Link from "next/link";
import { STATUS_META } from "@/lib/applications";
import { cn } from "@/lib/utils";
import type { PipelineStage, ScorePoint } from "@/types/dashboard";

/**
 * Applications per stage as labelled horizontal bars. One series, one hue: the count is written
 * next to every bar, so nothing depends on colour. The small dot matches the board's column colour.
 */
export function PipelineBars({ stages }: { stages: PipelineStage[] }) {
  const max = Math.max(1, ...stages.map((s) => s.count));
  return (
    <ul className="flex flex-col gap-3">
      {stages.map((stage) => (
        <li key={stage.status}>
          <Link
            href="/applications"
            className="group grid grid-cols-[6.5rem_minmax(0,1fr)_2rem] items-center gap-3 rounded-lg text-sm"
            aria-label={`${stage.label}: ${stage.count}`}
          >
            <span className="inline-flex items-center gap-2 text-muted-foreground group-hover:text-foreground">
              <span className={cn("size-2 rounded-full", STATUS_META[stage.status].dot)} aria-hidden />
              {stage.label}
            </span>
            <span className="h-2.5 overflow-hidden rounded-full bg-muted" aria-hidden>
              <span
                className="block h-full rounded-full bg-primary transition-[width] duration-500 group-hover:bg-primary/80"
                style={{ width: `${(stage.count / max) * 100}%` }}
              />
            </span>
            <span className="text-right font-semibold tabular-nums">{stage.count}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

const GRID = [100, 75, 50, 25, 0];

/**
 * Match score of each recently scored job, oldest → newest. Bars are links to the analysis;
 * hover or focus a bar for its job and score. A visually hidden table carries the same data.
 */
export function ScoreHistory({ points }: { points: ScorePoint[] }) {
  return (
    <figure className="flex flex-col gap-3">
      <div className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2">
        {/* y-axis labels */}
        <div className="relative h-44 text-right text-[11px] tabular-nums text-muted-foreground" aria-hidden>
          {GRID.map((value) => (
            <span key={value} className="absolute right-0 -translate-y-1/2" style={{ top: `${100 - value}%` }}>
              {value}
            </span>
          ))}
        </div>
        <div className="relative h-44">
          {/* recessive gridlines */}
          {GRID.map((value) => (
            <span
              key={value}
              aria-hidden
              className={cn("absolute inset-x-0 border-t", value === 0 ? "border-border" : "border-dashed border-border/60")}
              style={{ top: `${100 - value}%` }}
            />
          ))}
          <ol className="absolute inset-0 flex items-end gap-0.5 px-1">
            {points.map((point) => (
              <li key={point.job_id} className="group relative flex h-full flex-1 items-end justify-center">
                <Link
                  href={`/analyze?job=${point.job_id}`}
                  aria-label={`${point.title}${point.company ? ` at ${point.company}` : ""}: ${point.score}%`}
                  className="flex h-full w-full max-w-10 items-end justify-center rounded-t-[4px] outline-none"
                >
                  {/* hit target is the whole column; the visible mark is the bar */}
                  <span
                    className="block w-full max-w-7 rounded-t-[4px] bg-primary transition-colors group-hover:bg-primary/80 group-focus-within:bg-primary/80"
                    style={{ height: `${Math.max(point.score, 1)}%` }}
                  />
                </Link>
                <span
                  role="tooltip"
                  className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden w-max max-w-48 -translate-x-1/2 rounded-lg border border-border bg-popover px-2.5 py-1.5 text-xs shadow-soft group-focus-within:block group-hover:block"
                >
                  <span className="block truncate font-medium">{point.title}</span>
                  {point.company && <span className="block truncate text-muted-foreground">{point.company}</span>}
                  <span className="mt-0.5 block font-semibold tabular-nums">{point.score}% match</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <figcaption className="pl-10 text-xs text-muted-foreground">Oldest on the left, newest on the right. Click a bar to open the analysis.</figcaption>
      <table className="sr-only">
        <caption>Match score per analyzed job</caption>
        <thead>
          <tr>
            <th scope="col">Job</th>
            <th scope="col">Company</th>
            <th scope="col">Match</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.job_id}>
              <td>{point.title}</td>
              <td>{point.company}</td>
              <td>{point.score}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
