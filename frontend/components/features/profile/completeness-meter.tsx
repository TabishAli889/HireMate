"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Lightbulb } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { Completeness } from "@/lib/profile";

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Animated ring showing profile completeness, plus the top things to add next. */
export function CompletenessMeter({ score, tips }: Completeness) {
  const color = score >= 80 ? "hsl(var(--success))" : "hsl(var(--primary))";

  return (
    <Card className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
      <div className="relative mx-auto size-28 shrink-0 sm:mx-0">
        <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden>
          <circle cx="50" cy="50" r={RADIUS} fill="none" strokeWidth="9" style={{ stroke: "hsl(var(--muted))" }} />
          <motion.circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            strokeWidth="9"
            strokeLinecap="round"
            style={{ stroke: color }}
            strokeDasharray={CIRCUMFERENCE}
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset: CIRCUMFERENCE * (1 - score / 100) }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div
          className="absolute inset-0 grid place-items-center"
          role="meter"
          aria-label="Profile completeness"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={score}
        >
          <span className="font-heading text-2xl font-bold">
            {score}
            <span className="text-sm text-muted-foreground">%</span>
          </span>
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <h2 className="font-semibold">Profile completeness</h2>
        {tips.length === 0 ? (
          <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-success">
            <CheckCircle2 className="size-4" aria-hidden />
            Your profile is complete. Great matches ahead.
          </p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1.5">
            {tips.slice(0, 3).map((tip) => (
              <li key={tip} className="flex items-start gap-2 text-sm text-muted-foreground">
                <Lightbulb className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
                {tip}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
