import Link from "next/link";
import { ArrowUpRight, ScanSearch, SquareKanban, UserRound, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

interface Step {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

const STEPS: Step[] = [
  {
    title: "Build your Profile Vault",
    description: "Upload your resume PDF. HireMate structures it into skills, projects and experience you can edit.",
    href: "/profile",
    icon: UserRound,
  },
  {
    title: "Analyze a job posting",
    description: "Paste a posting or URL to get a match score, missing skills and tailored bullets — never invented.",
    href: "/analyze",
    icon: ScanSearch,
  },
  {
    title: "Track the application",
    description: "Move it from Saved to Offer on a board, with deadlines, notes and a timeline.",
    href: "/applications",
    icon: SquareKanban,
  },
];

/** Three-step onboarding cards shown on the dashboard before any data exists. */
export function GettingStarted() {
  return (
    <section aria-labelledby="getting-started-heading">
      <h2 id="getting-started-heading" className="mb-4 text-lg font-semibold">
        Get started in three steps
      </h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          return (
            <li key={step.href}>
              <Link href={step.href} className="group block h-full rounded-2xl">
                <Card className="flex h-full flex-col gap-4 p-6 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:border-primary/40">
                  <div className="flex items-center justify-between">
                    <span className="grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
                      <Icon className="size-5" aria-hidden />
                    </span>
                    <span className="font-heading text-sm font-semibold text-muted-foreground">0{index + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">{step.title}</h3>
                    <p className="mt-1.5 text-sm text-muted-foreground">{step.description}</p>
                  </div>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-primary">
                    Start
                    <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden />
                  </span>
                </Card>
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
