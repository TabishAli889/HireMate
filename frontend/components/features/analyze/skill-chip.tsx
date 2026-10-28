"use client";

import { Check, CircleDashed, Link2, TriangleAlert } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type ChipTone = "matched" | "related" | "missing" | "optional";

const STYLES: Record<ChipTone, { className: string; icon: typeof Check; srLabel: string }> = {
  matched: { className: "bg-success-soft text-success", icon: Check, srLabel: "matched" },
  related: { className: "border border-dashed border-success/60 bg-success-soft/50 text-success", icon: Link2, srLabel: "matched via related experience" },
  missing: { className: "bg-warning-soft text-warning", icon: TriangleAlert, srLabel: "missing, required" },
  optional: { className: "border border-warning/40 text-warning", icon: CircleDashed, srLabel: "missing, nice to have" },
};

interface SkillChipProps {
  skill: string;
  tone: ChipTone;
  /** Shown on hover/focus: where the profile shows this skill. */
  evidence?: string;
}

/** Skill pill whose colour and icon say matched / related / missing. */
export function SkillChip({ skill, tone, evidence }: SkillChipProps) {
  const { className, icon: Icon, srLabel } = STYLES[tone];
  const chip = (
    <span
      tabIndex={evidence ? 0 : undefined}
      className={cn("inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium", evidence && "cursor-help", className)}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      {skill}
      <span className="sr-only">
        {" "}
        ({srLabel}
        {evidence ? `: ${evidence}` : ""})
      </span>
    </span>
  );

  if (!evidence) return chip;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{chip}</TooltipTrigger>
      <TooltipContent className="max-w-xs">{evidence}</TooltipContent>
    </Tooltip>
  );
}
