import { CircleCheckBig, Clock, Footprints, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { MatchResult } from "@/types/job";

interface SkillPlanViewProps {
  match: MatchResult;
  onRescore: () => void;
  rescoring: boolean;
}

/** Ordered learning plan for the skills this job wants that the profile doesn't show. */
export function SkillPlanView({ match, onRescore, rescoring }: SkillPlanViewProps) {
  const missing = [...match.missing_required, ...match.missing_nice];
  const required = new Set(match.missing_required);

  if (missing.length === 0) {
    return (
      <Card className="flex items-start gap-3 p-6">
        <CircleCheckBig className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
        <div>
          <h2 className="font-semibold">No skill gaps for this role</h2>
          <p className="mt-1 text-sm text-muted-foreground">Your profile shows every skill the posting lists. Focus on tailoring your application.</p>
        </div>
      </Card>
    );
  }

  if (match.gap_plan.length === 0) {
    return (
      <Card className="flex flex-col items-start gap-3 p-6">
        <h2 className="font-semibold">Skills to learn: {missing.join(", ")}</h2>
        <p className="text-sm text-muted-foreground">A step-by-step plan couldn’t be generated this time.</p>
        <Button variant="outline" size="sm" onClick={onRescore} disabled={rescoring}>
          <RefreshCw className={rescoring ? "animate-spin" : undefined} aria-hidden />
          Try again
        </Button>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ol className="flex flex-col gap-4">
        {match.gap_plan.map((item) => (
          <li key={item.skill}>
            <Card className="flex gap-4 p-5 sm:p-6">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand font-heading text-base font-bold text-[hsl(var(--gradient-foreground))]">
                {item.priority}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-semibold">{item.skill}</h2>
                  <Badge variant={required.has(item.skill) ? "warning" : "outline"}>{required.has(item.skill) ? "Required" : "Nice to have"}</Badge>
                  {item.estimated_time && (
                    <Badge variant="muted">
                      <Clock className="size-3.5" aria-hidden />
                      {item.estimated_time}
                    </Badge>
                  )}
                </div>
                {item.why && <p className="mt-2 text-sm text-muted-foreground">{item.why}</p>}
                {item.first_steps.length > 0 && (
                  <ul className="mt-3 flex flex-col gap-2">
                    {item.first_steps.map((step) => (
                      <li key={step} className="flex gap-2.5 text-sm">
                        <Footprints className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                        {step}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Card>
          </li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        AI suggestions, in priority order. Once you’ve genuinely learned a skill, add it to your Profile Vault and re-score.
      </p>
    </div>
  );
}
