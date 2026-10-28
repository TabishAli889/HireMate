import { Building2, ExternalLink, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { SENIORITY_LABEL } from "@/lib/format";
import type { Job } from "@/types/job";

function SkillList({ title, skills }: { title: string; skills: string[] }) {
  if (skills.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <ul className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <li key={skill}>
            <Badge variant="outline">{skill}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** What the agent extracted from the posting. */
export function JobDetailsView({ job }: { job: Job }) {
  return (
    <Card className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          {job.company && (
            <span className="inline-flex items-center gap-1.5">
              <Building2 className="size-4" aria-hidden />
              {job.company}
            </span>
          )}
          {job.location && (
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="size-4" aria-hidden />
              {job.location}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge>{SENIORITY_LABEL[job.seniority]}</Badge>
          {job.employment_type && <Badge variant="muted">{job.employment_type}</Badge>}
        </div>
        {job.summary && <p className="leading-relaxed">{job.summary}</p>}
      </div>

      <SkillList title="Required skills" skills={job.required_skills} />
      <SkillList title="Nice to have" skills={job.nice_to_have_skills} />

      {job.responsibilities.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Key responsibilities</h3>
          <ul className="flex flex-col gap-2">
            {job.responsibilities.map((item) => (
              <li key={item} className="flex gap-2.5 text-sm">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {job.source_url && (
        <a
          href={job.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 self-start text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          View original posting
          <ExternalLink className="size-4" aria-hidden />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      )}
    </Card>
  );
}
