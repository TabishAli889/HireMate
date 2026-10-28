"use client";

import { useEffect, useId, useState } from "react";
import { animate, motion, useReducedMotion } from "framer-motion";
import { scoreBand } from "@/lib/format";
import { cn } from "@/lib/utils";

const RADIUS = 44;
const ARC = 0.75; // 270° gauge, gap at the bottom

const TONE_TEXT = { success: "text-success", primary: "text-primary", warning: "text-warning" } as const;

/** Animated 0-100 gauge with a count-up number and a plain-language band label. */
export function ScoreGauge({ score }: { score: number }) {
  const gradientId = `gauge-${useId().replace(/:/g, "")}`;
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(reduceMotion ? score : 0);
  const band = scoreBand(score);
  const stroke =
    band.tone === "success" ? "hsl(var(--success))" : band.tone === "warning" ? "hsl(var(--warning))" : `url(#${gradientId})`;

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(score);
      return;
    }
    const controls = animate(0, score, {
      duration: 1.1,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (value) => setDisplay(Math.round(value)),
    });
    return () => controls.stop();
  }, [score, reduceMotion]);

  return (
    <div className="flex flex-col items-center">
      <div
        className="relative size-44"
        role="meter"
        aria-label="Match score"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-valuetext={`${score} out of 100, ${band.label}`}
      >
        <svg viewBox="0 0 100 100" className="size-full rotate-[135deg]" aria-hidden>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" style={{ stopColor: "hsl(var(--gradient-from))" }} />
              <stop offset="100%" style={{ stopColor: "hsl(var(--gradient-to))" }} />
            </linearGradient>
          </defs>
          <motion.circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            style={{ stroke: "hsl(var(--muted))" }}
            initial={false}
            animate={{ pathLength: ARC }}
          />
          <motion.circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            style={{ stroke }}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: Math.max(0.001, (ARC * score) / 100) }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-heading text-5xl font-bold tabular-nums">{display}</span>
          <span className="text-xs font-medium text-muted-foreground">out of 100</span>
        </div>
      </div>
      <span className={cn("-mt-3 font-heading text-base font-semibold", TONE_TEXT[band.tone])}>{band.label}</span>
    </div>
  );
}
