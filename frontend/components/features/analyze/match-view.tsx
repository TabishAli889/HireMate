"use client";

import { CircleCheckBig, Info, RefreshCw } from "lucide-react";
import { ScoreGauge } from "@/components/features/analyze/score-gauge";
import { SkillChip } from "@/components/features/analyze/skill-chip";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SENIORITY_LABEL, formatRelative, parseUtc } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { MatchResult } from "@/types/job";

interface MatchViewProps {
  match: MatchResult;
  onRescore: () => void;
  rescoring: boolean;
  /** Current profile timestamp, to warn when the score is out of date. */
  profileUpdatedAt?: string;
}

function BreakdownRow({ label, matched, total }: { label: string; matched: number; total: number }) {
  const percent = total ? Math.round((matched / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-sm">
        <dt className="text-muted-foreground">{label}</dt>
        <dd className="font-medium tabular-nums">{total ? `${matched} / ${total}` : "Not listed"}</dd>
      </div>
      {total > 0 && <Progress value={percent} label={`${label}: ${matched} of ${total}`} />}
    </div>
  );
}

/** Score gauge, breakdown, explanation, and matched / missing skill chips. */
export function MatchView({ match, onRescore, rescoring, profileUpdatedAt }: MatchViewProps) {
  const { breakdown } = match;
  const stale = profileUpdatedAt !== undefined && parseUtc(profileUpdatedAt).getTime() - parseUtc(match.profile_updated_at).getTime() > 1000;
  const evidenceLookup = new Map(match.matched_skills.map((m) => [m.skill, m]));
  const hasRelated = match.matched_skills.some((m) => !m.direct);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
      <Card className="flex flex-col items-center gap-6 p-6">
        <ScoreGauge score={match.score} />
        <dl className="flex w-full flex-col gap-4">
          <BreakdownRow label="Required skills" matched={breakdown.required_matched} total={breakdown.required_total} />
          <BreakdownRow label="Nice to have" matched={breakdown.nice_matched} total={breakdown.nice_total} />
          <div className="flex items-center justify-between text-sm">
            <dt className="text-muted-foreground">Seniority fit</dt>
            <dd className="font-medium">
              {SENIORITY_LABEL[breakdown.seniority]} · {Math.round(breakdown.seniority_fit * 100)}%
            </dd>
          </div>
        </dl>
        <div className="flex w-full flex-col items-center gap-2 border-t border-border pt-4">
          <Button variant="outline" size="sm" onClick={onRescore} disabled={rescoring}>
            <RefreshCw className={cn(rescoring && "animate-spin")} aria-hidden />
            {rescoring ? "Re-scoring…" : "Re-score"}
          </Button>
          <p className="text-xs text-muted-foreground">Scored {formatRelative(match.scored_at)}</p>
        </div>
      </Card>

      <div className="flex min-w-0 flex-col gap-6">
        {stale && (
          <Card role="note" className="flex items-start gap-3 border-warning/40 p-4">
            <Info className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
            <p className="text-sm">
              Your profile changed after this score was calculated.{" "}
              <button type="button" onClick={onRescore} className="font-medium text-primary underline-offset-4 hover:underline">
                Re-score now
              </button>
            </p>
          </Card>
        )}

        <Card className="p-6">
          <h2 className="text-base font-semibold">Why this score</h2>
          <p className="mt-2 leading-relaxed">{match.explanation}</p>
          <p className="mt-4 text-xs text-muted-foreground">
            How it’s calculated: 70% required skills, 20% nice-to-haves, 10% seniority fit. Only skills your profile actually shows are counted.
          </p>
        </Card>

        <Card className="p-6">
          <h2 className="text-base font-semibold">
            Matched skills <span className="text-muted-foreground">({match.matched_skills.length})</span>
          </h2>
          {match.matched_skills.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">None of the listed skills appear in your profile yet.</p>
          ) : (
            <>
              <ul className="mt-3 flex flex-wrap gap-2">
                {match.matched_skills.map((m) => (
                  <li key={m.skill}>
                    <SkillChip skill={m.skill} tone={m.direct ? "matched" : "related"} evidence={evidenceLookup.get(m.skill)?.evidence} />
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-muted-foreground">
                Hover or focus a skill to see where your profile shows it.
                {hasRelated && " Dashed chips are matched through related experience, backed by an exact quote from your profile."}
              </p>
            </>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-base font-semibold">Missing skills</h2>
          {match.missing_required.length === 0 && match.missing_nice.length === 0 ? (
            <p className="mt-2 inline-flex items-center gap-2 text-sm text-success">
              <CircleCheckBig className="size-4" aria-hidden />
              You cover every skill this posting lists.
            </p>
          ) : (
            <div className="mt-3 flex flex-col gap-4">
              {match.missing_required.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Required</h3>
                  <ul className="flex flex-wrap gap-2">
                    {match.missing_required.map((skill) => (
                      <li key={skill}>
                        <SkillChip skill={skill} tone="missing" />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {match.missing_nice.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Nice to have</h3>
                  <ul className="flex flex-wrap gap-2">
                    {match.missing_nice.map((skill) => (
                      <li key={skill}>
                        <SkillChip skill={skill} tone="optional" />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                These stay out of your tailored resume and cover letter. See the Skill plan tab for what to learn first.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
